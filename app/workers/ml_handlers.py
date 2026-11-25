"""ML job handlers. Pure bounded computation; no provider/network calls."""

import json
import statistics


def profile_dataset(job, payload):
    """Summarize a bounded numeric dataset supplied in the job payload."""
    values = payload.get('values')
    if not isinstance(values, list) or not values or len(values) > 5000:
        raise ValueError('values must be a non-empty list of at most 5000 numbers')
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) for v in values):
        raise ValueError('values must contain only numbers')
    return {
        'count': len(values),
        'mean': round(statistics.fmean(values), 6),
        'median': round(statistics.median(values), 6),
        'min': min(values),
        'max': max(values),
        'population_std_dev': round(statistics.pstdev(values), 6) if len(values) > 1 else 0.0,
    }


def compare_metrics(job, payload):
    """Compare two bounded metric dictionaries using an explicit priority key."""
    left, right = payload.get('model_a'), payload.get('model_b')
    metric = payload.get('metric', 'f1')
    if not isinstance(metric, str) or metric not in {'accuracy', 'f1', 'precision', 'recall'}:
        raise ValueError('metric must be one of accuracy, f1, precision, recall')
    if not isinstance(left, dict) or not isinstance(right, dict):
        raise ValueError('model_a and model_b must be objects')
    if metric not in left or metric not in right:
        raise ValueError(f'both models must report {metric}')
    a, b = left[metric], right[metric]
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise ValueError(f'{metric} values must be numbers')
    winner = 'a' if a > b else 'b' if b > a else 'tie'
    return {'metric': metric, 'model_a': a, 'model_b': b, 'winner': winner,
            'difference': round(abs(a - b), 6)}


HANDLERS = {
    'ml_dataset_profile': profile_dataset,
    'ml_metrics_compare': compare_metrics,
}


def handle(job_id, job_type, payload_text):
    handler = HANDLERS.get(job_type)
    if handler is None:
        raise ValueError(f'no ML handler for {job_type!r}')
    payload = json.loads(payload_text)
    if not isinstance(payload, dict):
        raise ValueError('ML job payload must be a JSON object')
    return handler(None, payload)
