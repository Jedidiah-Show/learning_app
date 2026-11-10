"""Exercise filtering utilities based on metadata."""
from typing import List, Dict, Any


def filter_exercises(exercises: List[Dict[str, Any]], 
                     difficulty: str = None,
                     skills: List[str] = None,
                     lesson_id: str = None) -> List[Dict[str, Any]]:
    result = exercises
    if lesson_id:
        result = [e for e in result if e.get('lesson_id') == lesson_id]
    if difficulty:
        result = [e for e in result if e.get('difficulty') == difficulty]
    if skills:
        skill_set = set(skills)
        result = [e for e in result if skill_set.intersection(set(e.get('skills') or []))]
    return result


def get_available_filters(exercises: List[Dict[str, Any]]) -> Dict[str, Any]:
    difficulties = sorted(set(e.get('difficulty') for e in exercises if e.get('difficulty')))
    all_skills = set()
    for e in exercises:
        for s in (e.get('skills') or []):
            all_skills.add(s)
    return {
        'difficulties': difficulties,
        'skills': sorted(list(all_skills))
    }
