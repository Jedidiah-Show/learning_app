"""Video watch progress domain logic."""

from __future__ import annotations

from datetime import datetime, timezone

from app import db
from app.models import VideoProgress

MAX_VIDEO_SECONDS = 24 * 60 * 60
VIDEO_COMPLETION_RATIO = 0.9


def request_seconds(value, field):
    """Validate a non-negative numeric second value from the client."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{field} must be a number of seconds')
    if value < 0 or value > MAX_VIDEO_SECONDS:
        raise ValueError(f'{field} must be between 0 and {MAX_VIDEO_SECONDS}')
    return int(value)


def video_lengths(video, client_duration):
    """Return the clip start and length used to calculate watch progress."""
    start = video.get('start') or 0
    end = video.get('end')
    if end is not None:
        return start, max(0, end - start)
    curated_duration = video.get('duration_seconds')
    if client_duration:
        return start, max(0, client_duration - start)
    if curated_duration:
        return start, max(0, curated_duration - start)
    return start, None


def video_is_complete(watched_seconds, length):
    return bool(length) and watched_seconds >= length * VIDEO_COMPLETION_RATIO


def record_video_progress(user_id, lesson_id, video, *, position_seconds, client_duration=None, now=None):
    """Record furthest watch position; watch progress is advisory only."""
    now = now or datetime.now(timezone.utc)
    clip_start, clip_length = video_lengths(video, client_duration)
    position = max(position_seconds, clip_start)
    if clip_length is not None:
        position = min(position, clip_start + clip_length)
    watched_this_event = max(
        0,
        position - clip_start if clip_length is None else min(position - clip_start, clip_length),
    )

    progress = VideoProgress.query.filter_by(user_id=user_id, lesson_id=lesson_id).first()
    if progress is None:
        progress = VideoProgress(user_id=user_id, lesson_id=lesson_id, video_id=video['id'])
        db.session.add(progress)
    elif progress.video_id != video['id']:
        progress.video_id = video['id']
        progress.watched_seconds = 0
        progress.completed = False
        progress.completed_at = None

    progress.watched_seconds = max(progress.watched_seconds or 0, watched_this_event)
    progress.last_position = position
    if clip_length:
        progress.duration_seconds = clip_length
    completed_now = (not progress.completed) and video_is_complete(progress.watched_seconds, clip_length)
    if completed_now:
        progress.completed = True
        progress.completed_at = now
    progress.updated_at = now
    db.session.commit()
    return {
        'status': 'success',
        'lesson_id': lesson_id,
        'video_id': video['id'],
        'watched_seconds': progress.watched_seconds,
        'last_position': progress.last_position,
        'duration_seconds': progress.duration_seconds,
        'completed': progress.completed,
        'just_completed': completed_now,
    }
