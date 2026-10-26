"""Lesson video metadata derived from the bundled resource catalog.

Videos are curated ahead of time in ``app/data/dynamoai_resources.json``. This
module only parses and normalises that data; it never calls YouTube while a
learner is loading a lesson.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse


VIDEO_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{11}$')
_YOUTUBE_HOSTS = {
    'youtube.com',
    'www.youtube.com',
    'm.youtube.com',
    'music.youtube.com',
    'youtube-nocookie.com',
    'www.youtube-nocookie.com',
}
_TIMESTAMP_PATTERN = re.compile(r'^\d+(?::\d{1,2}){0,2}(?:\.\d+)?$')


def parse_timestamp(value):
    """Return a non-negative number of seconds from an int, float, or time string."""
    if value is None or value == '' or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        seconds = int(value)
    elif isinstance(value, str):
        text = value.strip()
        if not _TIMESTAMP_PATTERN.match(text):
            return None
        parts = text.split(':')
        try:
            seconds = 0
            for part in parts:
                seconds = seconds * 60 + float(part)
        except ValueError:
            return None
        seconds = int(seconds)
    else:
        return None
    return seconds if seconds >= 0 else None


def parse_video_id(url):
    """Extract an 11-character YouTube video id from a supported URL."""
    if not isinstance(url, str) or not url.strip():
        return None
    parsed = urlparse(url.strip())
    host = (parsed.hostname or '').lower()
    if host not in _YOUTUBE_HOSTS and host != 'youtu.be':
        return None

    if host == 'youtu.be':
        candidate = parsed.path.strip('/').split('/', 1)[0]
    elif parsed.path in {'/watch', '/watch/'}:
        candidate = (parse_qs(parsed.query).get('v') or [''])[0]
    else:
        parts = [part for part in parsed.path.split('/') if part]
        if len(parts) >= 2 and parts[0] in {
            'embed', 'shorts', 'live', 'v', 'e',
        }:
            candidate = parts[1]
        elif len(parts) == 1 and VIDEO_ID_PATTERN.match(parts[0]):
            candidate = parts[0]
        else:
            candidate = ''
    return candidate if VIDEO_ID_PATTERN.match(candidate) else None


def _video_id_from_value(value):
    """Accept either a bare video id (from enrichment) or a YouTube URL."""
    if isinstance(value, str) and VIDEO_ID_PATTERN.match(value.strip()):
        return value.strip()
    return parse_video_id(value)


def build_lesson_video(resource):
    """Return the normalised video for a lesson resource, or ``None``."""
    if not isinstance(resource, dict):
        return None
    video_id = (
        _video_id_from_value(resource.get('video_id'))
        or parse_video_id(resource.get('url'))
    )
    if not video_id:
        return None

    start = parse_timestamp(resource.get('start'))
    end = parse_timestamp(resource.get('end'))
    duration = parse_timestamp(resource.get('duration_seconds'))
    if start is not None and end is not None and end <= start:
        end = None
    if end is not None:
        duration = max(0, end - (start or 0))

    return {
        'id': video_id,
        'title': str(resource.get('title') or 'Lesson video').strip(),
        'url': f'https://www.youtube.com/watch?v={video_id}',
        'embed_url': (
            f'https://www.youtube-nocookie.com/embed/{video_id}'
            '?rel=0&playsinline=1&enablejsapi=1'
        ),
        'thumbnail_url': f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg',
        'channel': str(resource.get('channel') or '').strip(),
        'why': str(resource.get('why') or '').strip(),
        'start': start or 0,
        'end': end,
        'duration_seconds': duration,
    }


def format_duration(seconds):
    """Format seconds as ``m:ss`` or ``h:mm:ss`` for the lesson page."""
    if not isinstance(seconds, int) or isinstance(seconds, bool) or seconds < 0:
        return ''
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f'{hours}:{minutes:02d}:{seconds:02d}'
    return f'{minutes}:{seconds:02d}'
