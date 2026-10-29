"""Audit bundled course and exercise data for release-blocking gaps.

Run from the repository root:

    .venv/bin/python scripts/audit_curriculum.py
    .venv/bin/python scripts/audit_curriculum.py --strict-reviews

Hard defects exit non-zero. ``--strict-reviews`` also fails when a
version-sensitive lesson is still awaiting review. The default run prints the
review queue without blocking a local development build.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
import textwrap
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'app' / 'data'
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MODERN_TOPIC_IDS = ('3.16', '3.17', '3.18', '6.18', '7.18')
ARTIFACT_PATTERNS = (
    'Complete Lesson Guides',
    'Three pages per lesson',
    'YOUR WORKING NOTES',
    'CHECKPOINT CHECKLIST',
    'SHORT QUESTIONS',
    'PAGE ',
)
STRUCTURED_FIELDS = (
    'title', 'subtitle', 'goal', 'why_it_matters', 'outcomes', 'core_concepts',
    'key_terms', 'mental_model', 'worked_example', 'steps', 'tasks',
    'capstone_connection', 'questions', 'project', 'project_deliverables',
)


def _load(name):
    path = DATA / name
    return json.loads(path.read_text(encoding='utf-8'))


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _validate_url(value):
    return (
        isinstance(value, str)
        and value.startswith('https://')
        and len(value) > len('https://')
    )


def _validate_resources(errors, lessons, modules, resources, extras):
    lesson_ids = {lesson['id'] for lesson in lessons}
    module_ids = {module['id'] for module in modules}
    for key, entry in resources.items():
        if not isinstance(entry, dict):
            errors.append(f'Resource {key} is not an object')
            continue
        for kind, resource in entry.items():
            if kind == 'video' and resource is None:
                continue
            if not isinstance(resource, dict):
                errors.append(f'Resource {key}.{kind} is not an object')
                continue
            if not isinstance(resource.get('title'), str) or not resource['title'].strip():
                errors.append(f'Resource {key}.{kind} has no title')
            if not _validate_url(resource.get('url')):
                errors.append(f'Resource {key}.{kind} needs an HTTPS URL')
        if key.startswith('module:'):
            if key.split(':', 1)[1] not in module_ids:
                errors.append(f'Resource fallback {key} references an unknown module')
        elif key not in lesson_ids:
            errors.append(f'Resource {key} references an unknown lesson')
    for module in modules:
        if f"module:{module['id']}" not in resources:
            errors.append(f"Module {module['id']} has no resource fallback")
    for lesson in lessons:
        if lesson['id'] not in resources and f"module:{lesson['module_id']}" not in resources:
            errors.append(f"Lesson {lesson['id']} has no lesson or module resource")
    for lesson_id, entry in extras.items():
        if lesson_id not in lesson_ids:
            errors.append(f'Extra {lesson_id} references an unknown lesson')
        if not isinstance(entry, dict):
            errors.append(f'Extra {lesson_id} is not an object')
            continue
        if not isinstance(entry.get('intro'), str) or not entry['intro'].strip():
            errors.append(f'Extra {lesson_id} has no intro')
        if not isinstance(entry.get('concepts'), list) or not entry['concepts']:
            errors.append(f'Extra {lesson_id} has no concepts')
        if not isinstance(entry.get('answers'), list):
            errors.append(f'Extra {lesson_id} has no answer list')
    for lesson_id in MODERN_TOPIC_IDS:
        lesson = next((item for item in lessons if item['id'] == lesson_id), None)
        if lesson is None:
            errors.append(f'Modern topic lesson {lesson_id} is missing')
            continue
        if lesson_id not in resources and f"module:{lesson['module_id']}" not in resources:
            errors.append(f'Modern topic lesson {lesson_id} has no resource')
        if lesson_id not in extras:
            errors.append(f'Modern topic lesson {lesson_id} has no plain-language extra')


def _validate_placement(errors, course, lesson_ids):
    placement = course.get('placement') or {}
    questions = placement.get('questions') or []
    if len(questions) != 10:
        errors.append('Placement check must contain exactly 10 questions')
    passing = placement.get('passing_score')
    if not isinstance(passing, int) or isinstance(passing, bool) or not 0 < passing <= len(questions):
        errors.append('Placement passing_score must be between 1 and the question count')
    seen = set()
    for question in questions:
        if not isinstance(question, dict):
            errors.append('Placement question is not an object')
            continue
        qid = question.get('id')
        if not qid or qid in seen:
            errors.append(f'Placement question id is missing or duplicated: {qid!r}')
        seen.add(qid)
        options = question.get('options')
        if not isinstance(options, list) or len(options) < 2:
            errors.append(f'Placement question {qid} needs at least two options')
        answer = question.get('answer')
        if not isinstance(answer, int) or isinstance(answer, bool) or not 0 <= answer < len(options or []):
            errors.append(f'Placement question {qid} has an invalid answer index')
    skippable = placement.get('skippable_lessons') or []
    if not isinstance(skippable, list) or not skippable:
        errors.append('Placement check has no skippable lessons')
    for lesson_id in skippable:
        if lesson_id not in lesson_ids:
            errors.append(f'Placement references unknown lesson {lesson_id}')
        if not str(lesson_id).startswith(('0.', '1.0')):
            errors.append(f'Placement skip {lesson_id} is outside the foundation ramp')


def _validate_tracks(errors):
    try:
        from app.course_blueprint import TRACKS
    except ImportError as error:  # pragma: no cover - environment failure
        errors.append(f'Could not import course blueprint: {error}')
        return
    accelerated = TRACKS.get('accelerated') or {}
    standard = TRACKS.get('standard') or {}
    if accelerated.get('months') != 5:
        errors.append('Accelerated track must contain five months')
    if standard.get('months') != 10:
        errors.append('Standard track must contain ten months')
    module_ids = [module['id'] for module in _load('dynamoai_curriculum.json').get('modules', [])]
    for name, track in (('accelerated', accelerated), ('standard', standard)):
        months = track.get('milestones') or []
        if len(months) != track.get('months'):
            errors.append(f'{name} track month count does not match its milestones')
        grouped = [
            module_id for month in months for module_id in (month.get('modules') or [])
        ]
        if sorted(grouped) != sorted(module_ids):
            errors.append(f'{name} track must cover every module exactly once')
        for month in months:
            for field in ('number', 'title', 'summary', 'concepts', 'weeks', 'milestone'):
                if not month.get(field):
                    errors.append(f"{name} month {month.get('number')} has no {field}")


def _validate_reviews(errors, overrides, strict):
    queue = []
    for lesson_id, lesson_meta in (overrides.get('lessons') or {}).items():
        maintenance = lesson_meta.get('maintenance')
        if not maintenance:
            continue
        if maintenance.get('kind') != 'version-sensitive':
            errors.append(f'Lesson {lesson_id} has an invalid maintenance kind')
        if maintenance.get('review_status') not in {'reviewed', 'review-needed'}:
            errors.append(f'Lesson {lesson_id} needs an explicit maintenance status')
        if not maintenance.get('references'):
            errors.append(f'Lesson {lesson_id} has no primary documentation link')
        if maintenance.get('review_status') == 'reviewed':
            if not maintenance.get('reviewed_on') or not maintenance.get('references'):
                errors.append(f'Lesson {lesson_id} review is missing its date or primary source')
            try:
                age = (date.today() - date.fromisoformat(maintenance['reviewed_on'])).days
                if age > maintenance.get('review_interval_days', 90):
                    errors.append(f'Lesson {lesson_id} version review has expired')
            except (TypeError, ValueError, KeyError):
                errors.append(f'Lesson {lesson_id} has an invalid review date')
        else:
            queue.append(lesson_id)
    if strict and queue:
        errors.append(f'{len(queue)} version-sensitive lessons are awaiting review')
    return queue


def _validate_code(errors, lessons):
    for lesson in lessons:
        for field in STRUCTURED_FIELDS:
            value = lesson.get(field)
            if value is None:
                continue
            for text in _strings(value):
                compact = ' '.join(text.split())
                if any(pattern in compact for pattern in ARTIFACT_PATTERNS):
                    errors.append(f"Lesson {lesson['id']} has a page artifact in {field}")
                    break
        code = lesson.get('code')
        if isinstance(code, dict):
            snippet = code.get('code')
            language = (code.get('language') or '').lower()
            if isinstance(snippet, str) and snippet.strip() and language in {'python', 'py', ''}:
                try:
                    ast.parse(snippet)
                except SyntaxError as error:
                    errors.append(
                        f"Lesson {lesson['id']} Python snippet does not parse: {error}"
                    )


def _validate_exercises(errors, exercises):
    for exercise in exercises:
        code = (exercise.get('solution_code') or '') + '\n' + (exercise.get('checks_code') or '')
        if re.search(r'(?m)^await\s', code):
            code = (
                'import asyncio\nasync def __audit_main():\n'
                + textwrap.indent(code, '    ')
                + '\nasyncio.run(__audit_main())\n'
            )
        try:
            result = subprocess.run(
                [sys.executable, '-c', code],
                cwd=ROOT,
                timeout=15,
                capture_output=True,
                text=True,
            )
        except subprocess.TimeoutExpired:
            errors.append(f"Exercise {exercise.get('id')} checks timed out")
            continue
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or '').strip().splitlines()
            errors.append(
                f"Exercise {exercise.get('id')} checks failed: "
                f"{detail[-1] if detail else 'unknown error'}"
            )


def audit(strict_reviews=False, run_exercises=True):
    curriculum = _load('dynamoai_curriculum.json')
    exercises = _load('practice_exercises.json')
    resources = _load('dynamoai_resources.json')
    extras = _load('lesson_extras.json')
    overrides_path = DATA / 'curriculum_overrides.json'
    overrides = json.loads(overrides_path.read_text(encoding='utf-8')) if overrides_path.exists() else {}
    errors = []
    modules = curriculum.get('modules') or []
    lessons = curriculum.get('lessons') or []
    module_ids = [item.get('id') for item in modules]
    lesson_ids = [item.get('id') for item in lessons]
    if len(module_ids) != len(set(module_ids)):
        errors.append('Duplicate module ids')
    if len(lesson_ids) != len(set(lesson_ids)):
        errors.append('Duplicate lesson ids')
    if len(lessons) != curriculum.get('course', {}).get('total_lessons'):
        errors.append('Lesson count does not match the curriculum manifest')
    if any(item.get('module_id') not in set(module_ids) for item in lessons):
        errors.append('A lesson references an unknown module')
    for lesson in lessons:
        for field in ('title', 'pages'):
            value = lesson.get(field)
            if not value or (isinstance(value, list) and not any(str(part).strip() for part in value)):
                errors.append(f"Lesson {lesson.get('id', '?')} has no usable {field}")
        if not lesson.get('outcomes'):
            errors.append(f"Lesson {lesson.get('id', '?')} has no learning outcomes")
    seen_exercises = set()
    known_lessons = set(lesson_ids)
    for exercise in exercises:
        exercise_id = exercise.get('id')
        if not exercise_id or exercise_id in seen_exercises:
            errors.append(f'Duplicate or missing exercise id: {exercise_id!r}')
        seen_exercises.add(exercise_id)
        if exercise.get('lesson_id') not in known_lessons:
            errors.append(f"Exercise {exercise_id} references unknown lesson {exercise.get('lesson_id')!r}")
        for field in ('title', 'instructions', 'starter_code', 'checks_code'):
            if not isinstance(exercise.get(field), str) or not exercise[field].strip():
                errors.append(f'Exercise {exercise_id} has no usable {field}')
        if not isinstance(exercise.get('solution_code'), str) or not exercise['solution_code'].strip():
            errors.append(f'Exercise {exercise_id} has no worked solution')
        if not isinstance(exercise.get('estimated_minutes'), int) or exercise['estimated_minutes'] < 1:
            errors.append(f'Exercise {exercise_id} has no valid time estimate')
    lesson_modules = {lesson['id']: lesson.get('module_id') for lesson in lessons}
    exercise_counts = {}
    for exercise in exercises:
        module_id = lesson_modules.get(exercise.get('lesson_id'))
        if module_id:
            exercise_counts[module_id] = exercise_counts.get(module_id, 0) + 1
    for module in modules:
        module_id = module.get('id')
        minimum = 1 if module_id == '00' else 2
        if exercise_counts.get(module_id, 0) < minimum:
            errors.append(f'Module {module_id} needs at least {minimum} runnable exercises')
        module_meta = (overrides.get('modules') or {}).get(module_id, {})
        for field in ('assumed_prerequisites', 'readiness_check', 'project_deliverables', 'project_rubric', 'project_hours'):
            if not module_meta.get(field):
                errors.append(f'Module {module_id} has no {field} in the curriculum overlay')
    if not overrides.get('course', {}).get('content_maintenance_policy'):
        errors.append('Curriculum overlay has no content maintenance policy')
    if not overrides.get('course', {}).get('starting_assumption'):
        errors.append('Curriculum overlay has no stated starting assumption')
    if not {'beginner', 'experienced'}.issubset(
        set((overrides.get('course', {}).get('learning_routes') or {}).keys())
    ):
        errors.append('Curriculum overlay must describe beginner and experienced routes')
    _validate_resources(errors, lessons, modules, resources, extras)
    _validate_placement(errors, overrides.get('course') or {}, known_lessons)
    _validate_tracks(errors)
    _validate_code(errors, lessons)
    queue = _validate_reviews(errors, overrides, strict_reviews)
    if run_exercises:
        _validate_exercises(errors, exercises)
    return errors, len(modules), len(lessons), len(exercises), queue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--strict-reviews', action='store_true')
    parser.add_argument('--skip-exercises', action='store_true')
    args = parser.parse_args()
    problems, module_count, lesson_count, exercise_count, queue = audit(
        strict_reviews=args.strict_reviews,
        run_exercises=not args.skip_exercises,
    )
    if problems:
        for problem in problems:
            print(f'ERROR: {problem}')
        raise SystemExit(1)
    print(
        f'Course data OK: {module_count} modules, {lesson_count} lessons, '
        f'{exercise_count} exercises.'
    )
    print(f'Version-sensitive lessons awaiting review: {len(queue)}.')
    for lesson_id in queue:
        print(f'  review-needed: {lesson_id}')


if __name__ == '__main__':
    main()
