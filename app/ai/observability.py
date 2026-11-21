"""Privacy-conscious AI usage telemetry (M2.3/M2.6/M2.8).

Only metadata is persisted: task, provider, model, token counts, latency, cost
and error codes. Prompt bodies, responses and learner content are never stored.
Cost is estimated only from operator-configured rates; missing usage is left
unavailable.
"""

import uuid
from typing import Any, Optional

from flask import current_app, has_app_context, has_request_context
from flask_login import current_user
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.ai.schemas import TokenUsage


def new_request_id() -> str:
    return uuid.uuid4().hex


def _clip(value, length):
    if not isinstance(value, str):
        return None
    return value.strip()[:length] or None


def estimate_cost(provider: Optional[str], model: Optional[str], usage: TokenUsage) -> Optional[float]:
    """Estimate cost from configured rates, or return None when unavailable."""
    if usage.input_tokens is None and usage.output_tokens is None:
        return None
    if not has_app_context():
        return None
    rates = current_app.config.get('AI_MODEL_COSTS') or {}
    if not isinstance(rates, dict):
        return None
    entry = None
    for key in (model, provider):
        if key and isinstance(rates.get(key), dict):
            entry = rates[key]
            break
    if not isinstance(entry, dict):
        return None
    input_rate = entry.get('input_per_million_usd')
    output_rate = entry.get('output_per_million_usd')
    try:
        input_rate = float(input_rate) if input_rate is not None else None
        output_rate = float(output_rate) if output_rate is not None else None
    except (TypeError, ValueError):
        return None
    if input_rate is None and output_rate is None:
        return None
    cost = 0.0
    counted = False
    if usage.input_tokens is not None and input_rate is not None:
        cost += usage.input_tokens / 1_000_000 * input_rate
        counted = True
    if usage.output_tokens is not None and output_rate is not None:
        cost += usage.output_tokens / 1_000_000 * output_rate
        counted = True
    return round(cost, 6) if counted else None


def _current_user_id(explicit_id: Optional[int]) -> Optional[int]:
    if explicit_id is not None:
        return explicit_id
    if has_request_context():
        try:
            if current_user.is_authenticated:
                return current_user.id
        except Exception:
            return None
    return None


def record_ai_request(
    *,
    request_id: str,
    task_type: str,
    status: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    usage: Optional[TokenUsage] = None,
    duration_ms: int = 0,
    retry_count: int = 0,
    prompt_version: Optional[str] = None,
    correlation_id: Optional[str] = None,
    error_code: Optional[str] = None,
    user_id: Optional[int] = None,
) -> str:
    """Persist one metadata-only AI request record.

    Returns the request id so callers can correlate logs and responses. The
    write uses its own SQLAlchemy session and never participates in a request's
    business transaction.
    """
    usage = usage or TokenUsage()
    if has_app_context():
        try:
            from app import db
            from app.models import AIUsageRecord

            if inspect(db.engine).has_table('ai_usage_record'):
                record = AIUsageRecord(
                    request_id=request_id,
                    user_id=_current_user_id(user_id),
                    task_type=task_type,
                    provider=_clip(provider, 20),
                    model=_clip(model, 120),
                    status=status,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    estimated_cost_usd=usage.estimated_cost_usd,
                    duration_ms=max(0, int(duration_ms)),
                    retry_count=max(0, int(retry_count)),
                    prompt_version=_clip(prompt_version, 40),
                    correlation_id=_clip(correlation_id, 64),
                    error_code=error_code,
                )
                with Session(db.engine) as session:
                    session.add(record)
                    session.commit()
        except Exception as error:  # telemetry must never break generation
            current_app.logger.warning('Could not record AI usage: %s', error)
    return request_id


def usage_summary(days: int = 7) -> dict:
    """Aggregate recent AI usage for administrative display."""
    from datetime import timedelta

    from app import db
    from app.models import AIUsageRecord, utcnow

    cutoff = utcnow() - timedelta(days=max(1, int(days)))
    rows = db.session.query(
        AIUsageRecord.provider,
        AIUsageRecord.model,
        AIUsageRecord.task_type,
        db.func.count(AIUsageRecord.id),
        db.func.sum(AIUsageRecord.input_tokens),
        db.func.sum(AIUsageRecord.output_tokens),
        db.func.sum(AIUsageRecord.estimated_cost_usd),
        db.func.avg(AIUsageRecord.duration_ms),
    ).filter(AIUsageRecord.created_at >= cutoff).group_by(
        AIUsageRecord.provider, AIUsageRecord.model, AIUsageRecord.task_type
    ).all()
    return {
        'days': days,
        'groups': [
            {
                'provider': row[0],
                'model': row[1],
                'task_type': row[2],
                'requests': int(row[3] or 0),
                'input_tokens': int(row[4] or 0),
                'output_tokens': int(row[5] or 0),
                'estimated_cost_usd': round(float(row[6] or 0.0), 6),
                'average_duration_ms': round(float(row[7] or 0.0), 1),
            }
            for row in rows
        ],
    }
