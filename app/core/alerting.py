"""Deployment-specific ops alert delivery.

If ``OPS_ALERT_WEBHOOK_URL`` is configured, alert payloads are POSTed as JSON.
Delivery is best-effort and never blocks request handling.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from urllib import request as urlrequest

logger = logging.getLogger(__name__)

_LAST_SENT: dict[str, float] = {}


def _cooldown_seconds() -> int:
    try:
        return max(60, int(os.getenv('OPS_ALERT_COOLDOWN_SECONDS', '300')))
    except Exception:
        return 300


def send_ops_alert(alert: dict) -> bool:
    """Best-effort POST of an alert dict to OPS_ALERT_WEBHOOK_URL.

    Returns True if a delivery was attempted successfully. Alerts with the same
    ``type`` are rate-limited by OPS_ALERT_COOLDOWN_SECONDS.
    """
    url = (os.getenv('OPS_ALERT_WEBHOOK_URL') or '').strip()
    if not url:
        return False
    alert_type = str(alert.get('type') or 'unknown')
    now = __import__('time').time()
    last = _LAST_SENT.get(alert_type, 0)
    if now - last < _cooldown_seconds():
        return False
    _LAST_SENT[alert_type] = now

    payload = json.dumps(alert, default=str).encode('utf-8')
    req = urlrequest.Request(
        url, data=payload,
        headers={'Content-Type': 'application/json', 'User-Agent': 'ruach-ops-alert/1.0'},
        method='POST',
    )

    def _send():
        try:
            with urlrequest.urlopen(req, timeout=5) as resp:
                resp.read(64)
            logger.info('Ops alert delivered type=%s', alert_type)
        except Exception as exc:
            logger.warning('Ops alert delivery failed type=%s: %s', alert_type, exc)

    threading.Thread(target=_send, daemon=True).start()
    return True
