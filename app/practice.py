"""Curated, browser-runnable Python exercises for course lessons.

Both the shared AI Engineering course and the two specialization pathways
(Machine Learning Engineering, Cloud & AI Infrastructure) draw from the same
validation rules so every exercise the workspace can open is structurally
sound and its checks pass against the worked solution.
"""

from functools import lru_cache
import json
from pathlib import Path


EXERCISES_PATH = Path(__file__).parent / 'data' / 'practice_exercises.json'
PATHWAY_EXERCISES_PATH = Path(__file__).parent / 'data' / 'pathway_practice_exercises.json'


def _validate_exercise_list(exercises, source_label):
    if not isinstance(exercises, list):
        raise ValueError(f'Practice exercises in {source_label} must be a JSON list')
    by_id = {}
    for exercise in exercises:
        string_fields = {
            'id', 'lesson_id', 'title', 'instructions',
            'starter_code', 'checks_code',
        }
        required = string_fields | {
            'difficulty', 'skills', 'prerequisites',
        }
        if (
            not isinstance(exercise, dict)
            or not required.issubset(exercise)
            or any(not isinstance(exercise[key], str) for key in string_fields)
            or not exercise['id']
            or not exercise['lesson_id']
            or exercise['id'] in by_id
        ):
            raise ValueError(f'Practice exercise data is invalid in {source_label}')
        exercise = dict(exercise)
        if (
            not isinstance(exercise['difficulty'], str)
            or exercise['difficulty'] not in {'beginner', 'intermediate', 'advanced'}
            or not isinstance(exercise['skills'], list)
            or not exercise['skills']
            or any(not isinstance(skill, str) or not skill for skill in exercise['skills'])
            or not isinstance(exercise['prerequisites'], list)
            or any(
                not isinstance(prerequisite, str) or not prerequisite
                for prerequisite in exercise['prerequisites']
            )
        ):
            raise ValueError(f'Practice exercise metadata is invalid in {source_label}')
        by_id[exercise['id']] = exercise
    for exercise in by_id.values():
        if any(
            prerequisite not in by_id or prerequisite == exercise['id']
            for prerequisite in exercise['prerequisites']
        ):
            raise ValueError(f'Practice exercise prerequisite is invalid in {source_label}')
    return by_id


def _load(path):
    with path.open(encoding='utf-8') as source:
        return json.load(source)


@lru_cache(maxsize=1)
def all_practice_exercises():
    return _validate_exercise_list(_load(EXERCISES_PATH), str(EXERCISES_PATH))


@lru_cache(maxsize=1)
def all_pathway_practice_exercises():
    return _validate_exercise_list(
        _load(PATHWAY_EXERCISES_PATH), str(PATHWAY_EXERCISES_PATH),
    )


def practice_exercises_for_lesson(lesson_id):
    return [
        exercise for exercise in all_practice_exercises().values()
        if exercise['lesson_id'] == lesson_id
    ]


def pathway_exercises_for_lesson(lesson_id):
    return [
        exercise for exercise in all_pathway_practice_exercises().values()
        if exercise['lesson_id'] == lesson_id
    ]


def get_practice_exercise(exercise_id):
    return all_practice_exercises().get(str(exercise_id))


def get_pathway_practice_exercise(exercise_id):
    return all_pathway_practice_exercises().get(str(exercise_id))
