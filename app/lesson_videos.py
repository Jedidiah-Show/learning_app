"""Curated per-lesson YouTube video content (3–20 min), integrated into the LMS.

Every lesson in every pathway has a curated, verified video in
``app/data/curated_lesson_videos.json`` (source of truth also kept in
``docs/video_curation/`` and the review document ``video_content.docx``).
This module exposes lookups and attaches ``lesson['video']`` in the exact
shape produced by :func:`app.videos.build_lesson_video`, so all lesson
surfaces (AI Engineering, Shared Foundations, Machine Learning, Cloud & AI
Infrastructure, canonical ``ai.*`` manifest) render the same player.

A curated pick is used when a lesson has no explicitly-set video, and a
curated pick takes precedence when explicitly requested. Videos are real
YouTube ids; durations are 180–1200 s. Nothing here calls YouTube at runtime.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.videos import build_lesson_video

DATA_PATH = Path(__file__).parent / 'data' / 'curated_lesson_videos.json'

MIN_SECONDS = 180
MAX_SECONDS = 1200

CURATED_WHY = 'Curated 3–20 min video verified to reinforce this concept.'


@lru_cache(maxsize=1)
def curated_lesson_videos():
    """Return ``{lesson_id: record}`` for every curated lesson video."""
    try:
        with DATA_PATH.open(encoding='utf-8') as source:
            records = json.load(source)
    except (OSError, ValueError):
        return {}
    index = {}
    for rec in records:
        lid = rec.get('lesson_id')
        if lid:
            index[lid] = rec
    return index


def curated_video_record(lesson_id):
    """Return the curated record for ``lesson_id`` or ``None``."""
    if not lesson_id:
        return None
    return curated_lesson_videos().get(str(lesson_id))


def curated_lesson_video(lesson_id):
    """Return a normalized ``lesson['video']`` dict or ``None``."""
    rec = curated_video_record(lesson_id)
    if not rec:
        return None
    v = rec.get('video') or {}
    video_id = v.get('video_id')
    if not video_id:
        return None
    note = rec.get('match_note') or ''
    resource = {
        'video_id': video_id,
        'url': v.get('url') or f'https://www.youtube.com/watch?v={video_id}',
        'title': v.get('title') or rec.get('lesson_title') or 'Lesson video',
        'channel': v.get('channel') or '',
        'duration_seconds': v.get('duration_seconds'),
        'why': (CURATED_WHY + (' ' + note if note else '')).strip(),
    }
    video = build_lesson_video(resource)
    if video is None:
        return None
    # extra, honest curation metadata (harmless to templates)
    video['match_confidence'] = rec.get('match_confidence')
    video['match_note'] = rec.get('match_note')
    video['duration_mmss'] = v.get('duration_mmss')
    video['within_3_20min'] = bool(
        isinstance(video.get('duration_seconds'), int)
        and MIN_SECONDS <= video['duration_seconds'] <= MAX_SECONDS
    )
    video['curated'] = True
    video['alternates'] = rec.get('alternates') or []
    return video


def attach_curated_video(lesson, *, override=False):
    """Set ``lesson['video']`` from the curated catalog.

    ``override=False`` (default): keep an explicitly-set ``lesson['video']``
    if present; otherwise attach the curated pick. ``override=True``: always
    use the curated pick. Returns the lesson.
    """
    if not isinstance(lesson, dict):
        return lesson
    lesson_id = lesson.get('id') or lesson.get('lesson_id')
    existing = lesson.get('video')
    if existing and not override:
        return lesson
    video = curated_lesson_video(lesson_id)
    if video is not None:
        lesson['video'] = video
    return lesson
