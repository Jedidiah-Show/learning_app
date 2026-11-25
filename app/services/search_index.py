"""Search index helpers for lessons and pathways."""

from __future__ import annotations

from functools import lru_cache

from app.curriculum import all_lessons


def lesson_search_index():
    indexed = []
    for lesson in all_lessons():
        body = ' '.join(str(page) for page in lesson.get('pages') or [])
        text = ' '.join([
            lesson.get('title', ''), lesson.get('goal', ''),
            ' '.join(lesson.get('outcomes') or []),
            ' '.join(lesson.get('tasks') or []), body,
        ])
        indexed.append((lesson, text, text.lower()))
    return indexed


@lru_cache(maxsize=1)
def pathway_search_index():
    """Index the ML manifest separately: it ships as its own file."""
    from app.pathway_scope import pathway_lessons

    indexed = []
    for lesson in pathway_lessons('ml'):
        if lesson.get('source') != 'ml':
            continue
        sections = ' '.join(
            ' '.join([section.get('heading', ''), ' '.join(section.get('body') or [])])
            for section in lesson.get('sections') or []
        )
        text = ' '.join([
            lesson.get('title', ''), lesson.get('goal', ''),
            lesson.get('task', ''), sections,
        ])
        indexed.append((lesson, text, text.lower()))
    return indexed
