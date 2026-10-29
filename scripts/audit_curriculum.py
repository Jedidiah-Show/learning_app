"""Audit bundled course and exercise data for release-blocking gaps."""

import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'app' / 'data'


def audit():
    curriculum = json.loads((DATA / 'dynamoai_curriculum.json').read_text(encoding='utf-8'))
    exercises = json.loads((DATA / 'practice_exercises.json').read_text(encoding='utf-8'))
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
    for lesson_id, lesson_meta in (overrides.get('lessons') or {}).items():
        maintenance = lesson_meta.get('maintenance')
        if maintenance:
            if maintenance.get('kind') != 'version-sensitive':
                errors.append(f'Lesson {lesson_id} has an invalid maintenance kind')
            if maintenance.get('review_status') not in {'reviewed', 'review-needed'}:
                errors.append(f'Lesson {lesson_id} needs an explicit maintenance status')
            if not maintenance.get('references'):
                errors.append(f'Lesson {lesson_id} has no primary documentation link')
            if maintenance.get('review_status') == 'reviewed' and (
                not maintenance.get('reviewed_on') or not maintenance.get('references')
            ):
                errors.append(f'Lesson {lesson_id} review is missing its date or primary source')
            if maintenance.get('review_status') == 'reviewed':
                try:
                    age = (date.today() - date.fromisoformat(maintenance['reviewed_on'])).days
                    if age > maintenance.get('review_interval_days', 90):
                        errors.append(f'Lesson {lesson_id} version review has expired')
                except (TypeError, ValueError, KeyError):
                    errors.append(f'Lesson {lesson_id} has an invalid review date')
    if not overrides.get('course', {}).get('content_maintenance_policy'):
        errors.append('Curriculum overlay has no content maintenance policy')
    if not overrides.get('course', {}).get('starting_assumption'):
        errors.append('Curriculum overlay has no stated starting assumption')
    if not {'beginner', 'experienced'}.issubset(
        set((overrides.get('course', {}).get('learning_routes') or {}).keys())
    ):
        errors.append('Curriculum overlay must describe beginner and experienced routes')
    return errors, len(modules), len(lessons), len(exercises)


if __name__ == '__main__':
    problems, module_count, lesson_count, exercise_count = audit()
    if problems:
        for problem in problems:
            print(f'ERROR: {problem}')
        raise SystemExit(1)
    print(f'Course data OK: {module_count} modules, {lesson_count} lessons, {exercise_count} exercises.')
    overrides = json.loads((DATA / 'curriculum_overrides.json').read_text(encoding='utf-8'))
    review_queue = sum(
        item.get('maintenance', {}).get('review_status') == 'review-needed'
        for item in (overrides.get('lessons') or {}).values()
    )
    print(f'Version-sensitive lessons awaiting review: {review_queue}.')
