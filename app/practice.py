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
            'starter_code', 'checks_code',
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
        by_id[exercise['id']] = exercise
    return by_id


def practice_exercises_for_lesson(lesson_id):
    return [
        exercise for exercise in all_practice_exercises().values()
        if exercise['lesson_id'] == lesson_id
    ]


def get_practice_exercise(exercise_id):
    return all_practice_exercises().get(str(exercise_id))
