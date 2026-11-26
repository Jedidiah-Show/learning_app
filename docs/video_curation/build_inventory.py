"""Extract the complete lesson inventory for every pathway in the LMS.

Sources are the *actual* data sources the app renders, not assumptions:
- canonical registry (app.curriculum_registry): shared-foundations, ai-engineering, machine-learning
- learner-facing rendered catalog for AI Engineering (app.pathway_scope.ai_specialization_modules)
- cloud-ai-infrastructure independent catalog

Run with the app venv python from the repo root.
"""
import json
import os
import sys

sys.path.insert(0, '/home/jedidiah/learning_app')

from app.curriculum_registry import registry  # noqa: E402

OUT = os.environ.get('INVENTORY_OUT', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lessons_inventory.json'))


def lesson_rec(pathway_id, pathway_name, source, module, lesson, module_extra=None):
    return {
        'pathway_id': pathway_id,
        'pathway_name': pathway_name,
        'source': source,
        'module_id': module.get('id'),
        'module_number': module.get('number'),
        'module_title': module.get('title'),
        'module_description': (module.get('description') or module.get('summary') or '').strip(),
        'lesson_id': lesson.get('id'),
        'lesson_title': (lesson.get('title') or '').strip(),
        'lesson_goal': (lesson.get('goal') or lesson.get('subtitle') or '').strip(),
    }


def main():
    inventory = []

    # ---- Shared Foundations (canonical registry domain) -------------------
    sf = registry.get_domain('shared-foundations')
    # content manifest for richer titles/goals
    sf_content_path = '/home/jedidiah/learning_app/app/data/shared_foundations_lessons.json'
    with open(sf_content_path, encoding='utf-8') as fh:
        sf_content = json.load(fh)
    content_by_id = {
        lesson['id']: lesson
        for module in sf_content['modules']
        for lesson in module['lessons']
    }
    for module in sf.modules:
        for lesson in module['lessons']:
            merged = {**lesson, **content_by_id.get(lesson['id'], {})}
            inventory.append(lesson_rec(
                'shared-foundations', sf.name, 'shared_foundations_curriculum.json',
                module, merged))

    # ---- AI Engineering: canonical registry ------------------------------
    ai = registry.get_domain('ai-engineering')
    for module in ai.modules:
        for lesson in module['lessons']:
            inventory.append(lesson_rec(
                'ai-engineering', ai.name, 'ai_engineering_curriculum.json',
                module, lesson))

    # ---- AI Engineering: learner-facing rendered (legacy dynamoai) -------
    from app.pathway_scope import ai_specialization_modules  # noqa: E402
    rendered = ai_specialization_modules()
    for module in rendered:
        for lesson in module['lessons']:
            inventory.append(lesson_rec(
                'ai-engineering', 'AI Engineering',
                'app/data/dynamoai_curriculum.json (rendered catalog)',
                module, lesson))

    # ---- Machine Learning (canonical registry domain) --------------------
    ml = registry.get_domain('machine-learning')
    for module in ml.modules:
        for lesson in module['lessons']:
            inventory.append(lesson_rec(
                'machine-learning', ml.name, 'machine_learning_curriculum.json',
                module, lesson))

    # ---- Cloud & AI Infrastructure ---------------------------------------
    cai_path = '/home/jedidiah/learning_app/app/data/cloud_ai_infrastructure_pathway.json'
    with open(cai_path, encoding='utf-8') as fh:
        cai = json.load(fh)
    for module in cai['modules']:
        for lesson in module['lessons']:
            inventory.append(lesson_rec(
                'cloud-ai-infrastructure', cai.get('title') or 'Cloud & AI Infrastructure',
                'app/data/cloud_ai_infrastructure_pathway.json', module, lesson))

    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(inventory, fh, indent=1, ensure_ascii=False)

    # report
    from collections import Counter
    c = Counter((i['pathway_id'], i['source']) for i in inventory)
    for k, v in sorted(c.items()):
        print(k, v)
    print('TOTAL', len(inventory))
    # sanity: no empty titles, no dup ids within same source
    keys = [(i['pathway_id'], i['source'], i['lesson_id']) for i in inventory]
    assert len(keys) == len(set(keys)), 'duplicate keys!'
    assert all(i['lesson_title'] for i in inventory), 'empty title!'
    assert all(i['lesson_id'] for i in inventory), 'empty id!'


if __name__ == '__main__':
    main()
