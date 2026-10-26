#!/usr/bin/env python3
"""Audit the lesson video catalog and optionally verify it with YouTube.

Offline checks need no credentials:

    python scripts/validate_videos.py

Add a YouTube Data API key to check availability, embeddability and duration:

    YOUTUBE_API_KEY=... python scripts/validate_videos.py --online

The script never changes the catalog unless ``--write`` is passed. That flag
only fills in verified metadata (channel, duration and embeddable flag), so a
reviewed title/URL is never overwritten automatically.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CURRICULUM = ROOT / 'app' / 'data' / 'dynamoai_curriculum.json'
DEFAULT_RESOURCES = ROOT / 'app' / 'data' / 'dynamoai_resources.json'
YOUTUBE_VIDEOS_URL = 'https://www.googleapis.com/youtube/v3/videos'
ISO_DURATION = re.compile(
    r'^P(?:(?P<days>\d+)D)?'
    r'(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?'
    r'(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$'
)


def parse_iso_duration(value):
    match = ISO_DURATION.match(value or '')
    if not match:
        return None
    parts = match.groupdict(default='0')
    return int(
        float(parts['days']) * 86400
        + float(parts['hours']) * 3600
        + float(parts['minutes']) * 60
        + float(parts['seconds'])
    )


def parse_video_id(url):
    if not isinstance(url, str) or not url.strip():
        return None
    parsed = urllib.parse.urlparse(url.strip())
    host = (parsed.hostname or '').lower()
    if host == 'youtu.be':
        candidate = parsed.path.strip('/').split('/', 1)[0]
    elif host in {
        'youtube.com', 'www.youtube.com', 'm.youtube.com',
        'music.youtube.com', 'youtube-nocookie.com',
        'www.youtube-nocookie.com',
    }:
        if parsed.path in {'/watch', '/watch/'}:
            candidate = (urllib.parse.parse_qs(parsed.query).get('v') or [''])[0]
        else:
            parts = [part for part in parsed.path.split('/') if part]
            candidate = parts[1] if len(parts) >= 2 and parts[0] in {
                'embed', 'shorts', 'live', 'v', 'e',
            } else parts[0] if len(parts) == 1 else ''
    else:
        return None
    return candidate if re.fullmatch(r'[A-Za-z0-9_-]{11}', candidate) else None


def normalize_video_id(value):
    """Accept either a bare video id or a YouTube URL."""
    if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{11}', value.strip()):
        return value.strip()
    return parse_video_id(value)


def youtube_api(api_key, video_ids):
    """Return ``{video_id: item}`` for at most 50 ids per request."""
    results = {}
    for start in range(0, len(video_ids), 50):
        batch = video_ids[start:start + 50]
        query = urllib.parse.urlencode({
            'part': 'snippet,contentDetails,status',
            'id': ','.join(batch),
            'key': api_key,
            'maxResults': 50,
        })
        request = urllib.request.Request(
            f'{YOUTUBE_VIDEOS_URL}?{query}',
            headers={'Accept': 'application/json'},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as error:
            detail = error.read().decode('utf-8', errors='replace')[:300]
            raise SystemExit(
                f'YouTube API request failed ({error.code}): {detail}'
            ) from error
        except urllib.error.URLError as error:
            raise SystemExit(f'YouTube API request failed: {error.reason}') from error
        for item in payload.get('items', []):
            results[item['id']] = item
    return results


def audit(curriculum, resources, online_metadata=None):
    lessons = curriculum.get('lessons', [])
    modules = {module['id']: module for module in curriculum.get('modules', [])}
    lesson_ids = {lesson['id'] for lesson in lessons}
    errors, warnings = [], []
    seen_ids = defaultdict(list)
    coverage = Counter()
    module_totals = Counter()
    module_missing = defaultdict(list)
    online_metadata = online_metadata or {}

    for lesson in lessons:
        lesson_id = lesson['id']
        module_id = lesson['module_id']
        module_totals[module_id] += 1
        video = (resources.get(lesson_id) or {}).get('video')
        if not isinstance(video, dict):
            module_missing[module_id].append(lesson_id)
            warnings.append(f'{lesson_id}: no video')
            continue
        video_id = (
            normalize_video_id(video.get('video_id'))
            or parse_video_id(video.get('url'))
        )
        if not video_id:
            errors.append(f'{lesson_id}: missing or invalid YouTube URL')
            continue
        seen_ids[video_id].append(lesson_id)
        coverage[module_id] += 1
        start = video.get('start')
        end = video.get('end')
        if start not in (None, ''):
            try:
                start = int(start)
            except (TypeError, ValueError):
                errors.append(f'{lesson_id}: start must be a whole number of seconds')
                start = None
            if isinstance(start, int) and start < 0:
                errors.append(f'{lesson_id}: start cannot be negative')
        if end not in (None, ''):
            try:
                end = int(end)
            except (TypeError, ValueError):
                errors.append(f'{lesson_id}: end must be a whole number of seconds')
                end = None
            if isinstance(end, int) and end < 0:
                errors.append(f'{lesson_id}: end cannot be negative')
        if isinstance(start, int) and isinstance(end, int) and end <= start:
            errors.append(f'{lesson_id}: end must be greater than start')

        item = online_metadata.get(video_id)
        if online_metadata and item is None:
            errors.append(f'{lesson_id}: video {video_id} was not found on YouTube')
            continue
        if not item:
            continue
        status = item.get('status') or {}
        content = item.get('contentDetails') or {}
        snippet = item.get('snippet') or {}
        if status.get('privacyStatus') != 'public':
            errors.append(
                f'{lesson_id}: {video_id} is not public '
                f'({status.get("privacyStatus", "unknown")})'
            )
        if status.get('uploadStatus') not in (None, 'processed'):
            warnings.append(
                f'{lesson_id}: {video_id} upload status is '
                f'{status.get("uploadStatus")}'
            )
        if status.get('embeddable') is False:
            errors.append(f'{lesson_id}: {video_id} disables embedding')
        if (status.get('regionRestriction') or {}).get('blocked'):
            warnings.append(f'{lesson_id}: {video_id} is blocked in some regions')
        if not content.get('duration'):
            warnings.append(f'{lesson_id}: {video_id} has no duration metadata')
        if not snippet.get('title'):
            warnings.append(f'{lesson_id}: {video_id} has no title metadata')

    for video_id, reuse_lesson_ids in seen_ids.items():
        if len(reuse_lesson_ids) > 1:
            warnings.append(
                f'{video_id} is reused by {", ".join(reuse_lesson_ids)}'
            )
    for resource_id in sorted(set(resources) - lesson_ids):
        if not resource_id.startswith('module:'):
            warnings.append(f'{resource_id}: resource entry has no lesson')

    return {
        'lessons': len(lessons),
        'with_video': sum(coverage.values()),
        'without_video': len(lessons) - sum(coverage.values()),
        'coverage_by_module': {
            module_id: {
                'title': modules.get(module_id, {}).get('title', ''),
                'with_video': coverage[module_id],
                'total': module_totals[module_id],
                'missing': module_missing[module_id],
            }
            for module_id in sorted(module_totals)
        },
        'errors': errors,
        'warnings': warnings,
        'online_metadata': online_metadata,
    }


def enrich_resources(resources, online_metadata):
    """Add verified metadata without replacing curated titles or URLs."""
    changed = 0
    for resource in resources.values():
        video = resource.get('video') if isinstance(resource, dict) else None
        if not isinstance(video, dict):
            continue
        video_id = (
            normalize_video_id(video.get('video_id'))
            or parse_video_id(video.get('url'))
        )
        item = online_metadata.get(video_id)
        if not item:
            continue
        snippet = item.get('snippet') or {}
        content = item.get('contentDetails') or {}
        updates = {
            'video_id': video_id,
            'channel': snippet.get('channelTitle'),
            'duration_seconds': parse_iso_duration(content.get('duration')),
            'embeddable': (item.get('status') or {}).get('embeddable'),
        }
        for key, value in updates.items():
            if value is not None and video.get(key) != value:
                video[key] = value
                changed += 1
    return changed


def print_report(report):
    print(
        f"Lesson coverage: {report['with_video']}/{report['lessons']} "
        f"({report['without_video']} without a video)"
    )
    print('Module coverage:')
    for module_id, data in report['coverage_by_module'].items():
        missing = len(data['missing'])
        suffix = f' — missing {", ".join(data["missing"])}' if missing else ''
        print(
            f"  {module_id}  {data['with_video']:>2}/{data['total']:<2}  "
            f"{data['title']}{suffix}"
        )
    missing = [
        warning for warning in report['warnings']
        if warning.endswith(': no video')
    ]
    other_warnings = [
        warning for warning in report['warnings']
        if not warning.endswith(': no video')
    ]
    if missing:
        print(
            f"\nWarnings: {len(missing)} lessons have no curated video "
            '(see module coverage above).'
        )
    if other_warnings:
        print(f"\nOther warnings ({len(other_warnings)}):")
        for warning in other_warnings:
            print(f'  - {warning}')
    if report['errors']:
        print(f"\nErrors ({len(report['errors'])}):")
        for error in report['errors']:
            print(f'  - {error}')
    if not report['warnings'] and not report['errors']:
        print('\nNo catalog problems found.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--curriculum', type=Path, default=DEFAULT_CURRICULUM)
    parser.add_argument('--resources', type=Path, default=DEFAULT_RESOURCES)
    parser.add_argument('--api-key', default=os.environ.get('YOUTUBE_API_KEY'))
    parser.add_argument(
        '--online', action='store_true',
        help='Verify videos with the YouTube Data API (requires an API key)',
    )
    parser.add_argument(
        '--write', action='store_true',
        help='Write verified metadata back to the resources JSON',
    )
    parser.add_argument('--report', type=Path, help='Write the audit as JSON')
    parser.add_argument(
        '--require-all', action='store_true',
        help='Exit non-zero when any lesson is missing a video',
    )
    parser.add_argument(
        '--strict', action='store_true',
        help='Exit non-zero for warnings as well as errors',
    )
    args = parser.parse_args()

    curriculum = json.loads(args.curriculum.read_text(encoding='utf-8'))
    resources = json.loads(args.resources.read_text(encoding='utf-8'))

    online_metadata = None
    if args.online or args.api_key:
        if not args.api_key:
            parser.error('--online requires YOUTUBE_API_KEY or --api-key')
        ids = sorted({
            video_id
            for resource in resources.values()
            if isinstance(resource, dict)
            for video in [resource.get('video')]
            if isinstance(video, dict)
            for video_id in [normalize_video_id(video.get('video_id')) or parse_video_id(video.get('url'))]
            if video_id
        })
        print(f'Checking {len(ids)} unique video ids with YouTube...')
        online_metadata = youtube_api(args.api_key, ids)

    report = audit(curriculum, resources, online_metadata)
    print_report(report)

    if args.write:
        if not online_metadata:
            parser.error('--write requires online verification')
        changed = enrich_resources(resources, online_metadata)
        args.resources.write_text(
            json.dumps(resources, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
        print(f'\nUpdated {changed} metadata fields in {args.resources}')
    if args.report:
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
        print(f'Wrote report to {args.report}')

    if report['errors']:
        return 1
    if args.strict and report['warnings']:
        return 1
    if args.require_all and report['without_video']:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
