"""Audit bundled course and exercise data for release-blocking gaps."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'app' / 'data'


def audit():
    curriculum = json.loads((DATA / 'dynamoai_curriculum.json').read_text(encoding='utf-8'))
    exercises = json.loads((DATA / 'practice_exercises.json').read_text(encoding='utf-8'))
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
    return errors, len(modules), len(lessons), len(exercises)


if __name__ == '__main__':
    problems, module_count, lesson_count, exercise_count = audit()
    if problems:
        for problem in problems:
            print(f'ERROR: {problem}')
        raise SystemExit(1)
    print(f'Course data OK: {module_count} modules, {lesson_count} lessons, {exercise_count} exercises.')
