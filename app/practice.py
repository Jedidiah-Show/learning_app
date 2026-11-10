"""Curated, browser-runnable Python exercises for course lessons."""

from functools import lru_cache
import json
from pathlib import Path


EXERCISES_PATH = Path(__file__).parent / 'data' / 'practice_exercises.json'


@lru_cache(maxsize=1)
def all_practice_exercises():
    with EXERCISES_PATH.open(encoding='utf-8') as source:
        exercises = json.load(source)
    if not isinstance(exercises, list):
        raise ValueError('Practice exercises must be a JSON list')
    by_id = {}
    for exercise in exercises:
        required = {
            'id', 'lesson_id', 'title', 'instructions',
            'starter_code', 'checks_code', 'difficulty', 'skills',
            'prerequisites',
        }
        if (
            not isinstance(exercise, dict)
            or not required.issubset(exercise)
            or any(not isinstance(exercise[key], str) for key in required)
            or not exercise['id']
            or not exercise['lesson_id']
            or exercise['id'] in by_id
        ):
            raise ValueError('Practice exercise data is invalid')
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
            raise ValueError('Practice exercise metadata is invalid')
        by_id[exercise['id']] = exercise
    for exercise in by_id.values():
        if any(
            prerequisite not in by_id or prerequisite == exercise['id']
            for prerequisite in exercise['prerequisites']
        ):
            raise ValueError('Practice exercise prerequisite is invalid')
    return by_id


def practice_exercises_for_lesson(lesson_id):
    return [
        exercise for exercise in all_practice_exercises().values()
        if exercise['lesson_id'] == lesson_id
    ]


def get_practice_exercise(exercise_id):
    return all_practice_exercises().get(str(exercise_id))
