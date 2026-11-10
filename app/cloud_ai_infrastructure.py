"""Independent catalog for the Cloud & AI Infrastructure specialization."""

from functools import lru_cache
import json
from pathlib import Path


PATHWAY_PATH = Path(__file__).parent / 'data' / 'cloud_ai_infrastructure_pathway.json'
PATHWAY_ID = 'cloud-ai-infrastructure'


@lru_cache(maxsize=1)
def cloud_ai_infrastructure_pathway():
    with PATHWAY_PATH.open(encoding='utf-8') as source:
        pathway = json.load(source)
    if pathway.get('id') != PATHWAY_ID:
        raise ValueError('Cloud AI infrastructure pathway has an unexpected ID')
    return pathway


def cloud_ai_infrastructure_lessons():
    return [
        {**lesson, 'module_id': module['id'], 'module_title': module['title'],
         'module_number': module['number']}
        for module in cloud_ai_infrastructure_pathway()['modules']
        for lesson in module['lessons']
    ]


def get_cloud_ai_infrastructure_lesson(lesson_id):
    return next(
        (lesson for lesson in cloud_ai_infrastructure_lessons() if lesson['id'] == lesson_id),
        None,
    )
