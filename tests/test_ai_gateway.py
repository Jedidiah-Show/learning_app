"""M2.1–M2.3, M2.5, M2.7: provider gateway, routing, telemetry, prompts, eval."""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import requests

from app import create_app, db
from app.ai.evaluation import EvalCase, evaluate_dataset, run_structural_check
from app.ai.gateway import generate, generate_json
from app.ai.observability import estimate_cost
from app.ai.prompts import active_version, get_prompt, list_prompts, rollback
from app.ai.routing import resolve_route
from app.ai.schemas import AIRequest, TokenUsage
from app.models import AIUsageRecord
from app.openrouter import OpenRouterError


class FakeResponse:
    def __init__(self, payload, status_code=200, headers=None):
        self.payload = payload
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.headers = headers or {}

    def json(self):
        return self.payload


@pytest.fixture
def app():
    temp_dir = tempfile.TemporaryDirectory()
    previous = os.environ.get('DATABASE_URL')
    os.environ['DATABASE_URL'] = f'sqlite:///{temp_dir.name}/ai-gateway.db'
    app = create_app()
    app.config.update(
        TESTING=True,
        GEMINI_API_KEY='test-gemini-key',
        OPENROUTER_API_KEY=None,
        AI_CACHE_ENABLED=False,
    )
    with app.app_context():
        db.create_all()
    ctx = app.app_context()
    ctx.push()
    try:
        yield app
    finally:
        db.session.remove()
        ctx.pop()
        with app.app_context():
            db.drop_all()
            db.engine.dispose()
        if previous is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = previous
        temp_dir.cleanup()


def _gemini_response(text='{"ok": true}', usage=None):
    payload = {'candidates': [{'content': {'parts': [{'text': text}]}}]}
    if usage is not None:
        payload['usageMetadata'] = usage
    return FakeResponse(payload)


def test_gateway_normalizes_response_and_records_actual_usage(app):
    app.config['AI_MODEL_COSTS'] = {
        'gemini-3.8-flash': {
            'input_per_million_usd': 1.0,
            'output_per_million_usd': 2.0,
        }
    }
    with patch('app.gemini._post_gemini_request', return_value=_gemini_response(
        usage={'promptTokenCount': 1000, 'candidatesTokenCount': 200}
    )):
        response = generate(AIRequest(
            prompt='Return JSON', task_type='general', model_tier='flash',
            use_cache=False,
        ))

    assert response.data == {'ok': True}
    assert response.usage.input_tokens == 1000
    assert response.usage.output_tokens == 200
    assert response.usage.total_tokens == 1200
    assert response.usage.estimated_cost_usd == pytest.approx(0.0014)
    with app.app_context():
        record = AIUsageRecord.query.one()
        assert record.task_type == 'general'
        assert record.status == 'success'
        assert record.input_tokens == 1000
        assert record.estimated_cost_usd == pytest.approx(0.0014)
        assert not hasattr(record, 'prompt')


def test_missing_usage_and_cost_are_recorded_as_unavailable(app):
    with patch('app.gemini._post_gemini_request', return_value=_gemini_response()):
        response = generate_json('Return JSON', task_type='general', use_cache=False)
    assert response == {'ok': True}
    with app.app_context():
        record = AIUsageRecord.query.one()
        assert record.input_tokens is None
        assert record.estimated_cost_usd is None


def test_internal_provider_retries_are_counted_as_attempts(app):
    with patch.dict(os.environ, {'GEMINI_MAX_ATTEMPTS': '2'}), \
         patch('app.gemini._sleep_before_retry'), \
         patch('app.gemini._post_gemini_request', side_effect=[
             requests.Timeout('slow'),
             _gemini_response(usage={
                 'promptTokenCount': 10, 'candidatesTokenCount': 5,
             }),
         ]):
        response = generate(AIRequest(
            prompt='Return JSON', task_type='general', use_cache=False,
        ))
    assert response.data == {'ok': True}
    assert response.attempts == 2
    with app.app_context():
        record = AIUsageRecord.query.one()
        assert record.retry_count == 1


def test_openrouter_provider_reports_actual_usage(app):
    from app.openrouter import generate_json as openrouter_generate_json

    app.config['OPENROUTER_API_KEY'] = 'test-openrouter-key'
    captured = {}

    def sink(provider, model, input_tokens, output_tokens):
        captured.update({
            'provider': provider,
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
        })

    payload = {
        'choices': [{'message': {'content': '{"ok": true}'}}],
        'usage': {'prompt_tokens': 300, 'completion_tokens': 40},
    }
    with patch('app.openrouter._post_openrouter_request', return_value=FakeResponse(payload)):
        result = openrouter_generate_json('hello', model='flash', usage_sink=sink)
    assert result == {'ok': True}
    assert captured['provider'] == 'openrouter'
    assert captured['input_tokens'] == 300
    assert captured['output_tokens'] == 40


def test_task_routing_can_be_configured_centrally(app):
    app.config['AI_TASK_ROUTES'] = {
        'tutor_chat': {'provider': 'openrouter', 'model': 'pro'}
    }
    with patch('app.openrouter.generate_json', return_value={'answer': 'ok'}) as mocked:
        result = generate_json('hello', task_type='tutor_chat')
    assert result == {'answer': 'ok'}
    assert mocked.call_args.kwargs['model'] == 'pro'
    assert mocked.call_args.kwargs['read_timeout'] == 25
    assert mocked.call_args.kwargs['max_tokens'] == 512
    assert resolve_route('tutor_chat').provider == 'openrouter'


def test_openrouter_failure_can_fall_back_to_gemini(app):
    app.config['AI_TASK_ROUTES'] = {
        'general': {'provider': 'openrouter', 'fallback_provider': 'gemini'}
    }
    with patch('app.openrouter.generate_json', side_effect=OpenRouterError('offline')), \
         patch('app.gemini.generate_json', return_value={'ok': True}) as gemini:
        result = generate_json('hello', task_type='general')
    assert result == {'ok': True}
    assert gemini.call_args.kwargs['allow_fallback'] is False


def test_estimate_cost_requires_configured_rates(app):
    usage = TokenUsage(input_tokens=1000, output_tokens=500)
    assert estimate_cost('gemini', 'unknown-model', usage) is None
    app.config['AI_MODEL_COSTS'] = {
        'unknown-model': {
            'input_per_million_usd': 2,
            'output_per_million_usd': 4,
        }
    }
    assert estimate_cost('gemini', 'unknown-model', usage) == pytest.approx(0.004)


def test_prompt_registry_tracks_versions_and_rollback(app):
    assert active_version('tutor_chat') == 'v1'
    assert 'tutor_chat' in list_prompts()
    prompt = get_prompt('question_generation')
    assert prompt.version == 'v1'
    assert 'Create exactly {count}' in prompt.template
    assert prompt.render(count=5, quiz_type='lesson', context='material').startswith(
        'Create exactly 5'
    )
    assert rollback('question_generation', 'v1') == 'v1'
    with pytest.raises(ValueError):
        get_prompt('question_generation', 'v9')


def test_evaluation_framework_checks_structured_output():
    case = EvalCase('t-01', 'Explain this', expects=['mentions evidence'])
    assert run_structural_check(
        case, {'in_scope': True, 'answer': 'Use evidence.'}
    ).passed
    assert not run_structural_check(case, {'in_scope': True, 'answer': ''}).passed
    out_of_scope = EvalCase(
        't-02', 'Unrelated', case_type='out_of_scope', expects=[]
    )
    assert not run_structural_check(
        out_of_scope, {'in_scope': True, 'answer': 'Unrelated answer'}
    ).passed
    report = evaluate_dataset(
        [case], lambda _: {'in_scope': True, 'answer': 'Grounded answer.'}
    )
    assert report == {
        'total': 1, 'passed': 1, 'failed': 0,
        'results': [run_structural_check(
            case, {'in_scope': True, 'answer': 'Grounded answer.'}
        ).to_dict()],
    }


def test_bundled_tutor_datasets_load():
    from app.ai.evaluation.framework import dataset_paths, load_dataset
    paths = dataset_paths()
    assert len(paths) == 3
    assert all(os.path.exists(path) for path in paths)
    assert all(load_dataset(path) for path in paths)
