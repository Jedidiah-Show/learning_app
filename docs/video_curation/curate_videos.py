"""Curate a real, verified YouTube video (3-20 min) for every LMS lesson.

No hallucination: every pick is verified against the live YouTube watch page
(playability, not live/private, exact lengthSeconds within [180, 1200]).
Results are cached on disk so reruns are cheap and idempotent.
Lessons with no qualifying video are marked NO_MATCH explicitly, never skipped.
"""
import json
import math
import os
import re
import sys
import time
from urllib.parse import urlencode

import requests

BASE = os.environ.get('VIDEO_CURATION_DIR', os.path.dirname(os.path.abspath(__file__)))
INVENTORY = os.environ.get('INVENTORY', os.path.join(BASE, 'lessons_inventory.json'))
OUT = os.environ.get('CURATED_OUT', os.path.join(BASE, 'curated_videos.json'))
SEARCH_CACHE = os.path.join(BASE, 'cache_search.json')
WATCH_CACHE = os.path.join(BASE, 'cache_watch.json')
RESOURCES = os.environ.get('DYNAMOAI_RESOURCES', '/home/jedidiah/learning_app/app/data/dynamoai_resources.json')

MIN_SECONDS = 180          # 3 minutes
MAX_SECONDS = 1200         # 20 minutes
MAX_CANDIDATES_PER_LESSON = 5
SEARCH_RESULTS = 12
REQUEST_DELAY = 0.45
MAX_RETRIES = 4

HEADERS = {
    'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'),
    'Accept-Language': 'en-US,en;q=0.9',
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# --- tiny caches -----------------------------------------------------------
def _load(path):
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}

def _save(path, data):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path)

SEARCH_CACHE_D = _load(SEARCH_CACHE)
WATCH_CACHE_D = _load(WATCH_CACHE)

# --- text utils ------------------------------------------------------------
STOP = set(('a an and are as at be by for from how in into is it its of on or '
            'that the this to what when with your you we i do does using use '
            'tutorial lesson intro introduction basics beginners beginner '
            'explained explain simple part episode video full course '
            'session talk series chapter guide vs versus 101 crash').split())

def tokens(text):
    text = re.sub(r'[^a-z0-9\s]', ' ', (text or '').lower())
    return [t for t in text.split() if t and t not in STOP and len(t) > 1]

def overlap_score(query_tokens, title_tokens):
    if not query_tokens or not title_tokens:
        return 0.0
    q = set(query_tokens)
    t = set(title_tokens)
    inter = len(q & t)
    if inter == 0:
        return 0.0
    # coverage of query + coverage of title, balanced
    precision = inter / len(t)
    recall = inter / len(q)
    return round((precision + recall) / 2, 4)

# --- HTTP ------------------------------------------------------------------
def http_get(url, params=None):
    for attempt in range(MAX_RETRIES):
        try:
            resp = SESSION.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                time.sleep(2 ** attempt + 1)
                continue
            if resp.status_code >= 500:
                time.sleep(1.5 * (attempt + 1))
                continue
            return resp
        except requests.RequestException:
            time.sleep(1.5 * (attempt + 1))
    return None

# --- YouTube parsing -------------------------------------------------------
def parse_iso8601_duration(text):
    if not text:
        return None
    m = re.match(r'^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$', text)
    if not m:
        return None
    h, mn, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mn * 60 + s

def extract_initial_data(html):
    m = re.search(r'ytInitialData\s*=\s*(\{.*?\});</script>', html, re.S)
    if not m:
        m = re.search(r'ytInitialData"\s*:\s*(\{.*?\});', html, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except ValueError:
        return None

def find_video_renderers(node, acc):
    if isinstance(node, dict):
        if 'videoRenderer' in node and isinstance(node['videoRenderer'], dict):
            acc.append(node['videoRenderer'])
        for v in node.values():
            find_video_renderers(v, acc)
    elif isinstance(node, list):
        for v in node:
            find_video_renderers(v, acc)

def search_youtube(query):
    key = query.strip().lower()
    if key in SEARCH_CACHE_D:
        return SEARCH_CACHE_D[key]
    url = 'https://www.youtube.com/results?' + urlencode({'search_query': query, 'hl': 'en'})
    resp = http_get(url)
    results = []
    if resp is not None and resp.status_code == 200:
        data = extract_initial_data(resp.text)
        renderers = []
        if data:
            find_video_renderers(data, renderers)
        seen = set()
        for vr in renderers:
            vid = vr.get('videoId')
            if not vid or vid in seen:
                continue
            seen.add(vid)
            title = ''
            t = vr.get('title')
            if isinstance(t, dict):
                title = t.get('simpleText') or ''.join(
                    r.get('text', '') for r in (t.get('runs') or []))
            channel = ''
            oc = vr.get('ownerText') or vr.get('longBylineText') or {}
            if isinstance(oc, dict):
                channel = ''.join(r.get('text', '') for r in (oc.get('runs') or []))
            length_text = None
            lt = vr.get('lengthText')
            if isinstance(lt, dict):
                length_text = lt.get('simpleText')
            results.append({
                'video_id': vid,
                'title': title,
                'channel': channel,
                'length_text': length_text,
                'source': 'search',
            })
            if len(results) >= SEARCH_RESULTS:
                break
    SEARCH_CACHE_D[key] = results
    _save(SEARCH_CACHE, SEARCH_CACHE_D)
    time.sleep(REQUEST_DELAY)
    return results

def verify_watch(video_id):
    """Authoritative verification against the live watch page."""
    if video_id in WATCH_CACHE_D:
        return WATCH_CACHE_D[video_id]
    url = 'https://www.youtube.com/watch'
    resp = http_get(url, params={'v': video_id, 'hl': 'en'})
    info = {
        'video_id': video_id,
        'ok': False,
        'duration_seconds': None,
        'title': None,
        'channel': None,
        'playability': None,
        'is_live': None,
        'is_private': None,
        'is_unlisted': None,
        'verified_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'checked_url': f'https://www.youtube.com/watch?v={video_id}',
    }
    if resp is not None and resp.status_code == 200:
        html = resp.text
        m = re.search(r'"lengthSeconds":"(\d+)"', html)
        info['duration_seconds'] = int(m.group(1)) if m else None
        m = re.search(r'"playabilityStatus":\{"status":"([A-Z_]+)"', html)
        info['playability'] = m.group(1) if m else None
        m = re.search(r'"isLiveContent":(true|false)', html)
        info['is_live'] = (m.group(1) == 'true') if m else None
        m = re.search(r'"isPrivate":(true|false)', html)
        info['is_private'] = (m.group(1) == 'true') if m else None
        m = re.search(r'"isUnlisted":(true|false)', html)
        info['is_unlisted'] = (m.group(1) == 'true') if m else None
        # title
        m = re.search(r'"title":\{"simpleText":"((?:[^"\\]|\\.)*)"', html)
        if m:
            try:
                info['title'] = json.loads('"' + m.group(1) + '"')
            except ValueError:
                info['title'] = m.group(1)
        else:
            m = re.search(r'<title>(.*?)</title>', html, re.S)
            if m:
                info['title'] = re.sub(r'\s*-\s*YouTube\s*$', '', m.group(1).strip())
        m = re.search(r'"ownerChannelName":"((?:[^"\\]|\\.)*)"', html)
        if m:
            try:
                info['channel'] = json.loads('"' + m.group(1) + '"')
            except ValueError:
                info['channel'] = m.group(1)
        # embeddability
        m = re.search(r'"playableInEmbed":(true|false)', html)
        info['playable_in_embed'] = (m.group(1) == 'true') if m else None
        # age restriction
        info['age_restricted'] = bool(re.search(r'"isAgeRestricted":true', html)) or \
            'Sign in to confirm your age' in html
    dur = info['duration_seconds']
    info['duration_mmss'] = mmss(dur)
    info['within_3_20min'] = (dur is not None and MIN_SECONDS <= dur <= MAX_SECONDS)
    info['ok'] = bool(
        info['within_3_20min']
        and info['playability'] in (None, 'OK')
        and not info['is_live']
        and not info['is_private']
        and info['title']
    )
    WATCH_CACHE_D[video_id] = info
    _save(WATCH_CACHE, WATCH_CACHE_D)
    time.sleep(REQUEST_DELAY)
    return info

def mmss(seconds):
    if seconds is None:
        return None
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f'{h}:{m:02d}:{s:02d}'
    return f'{m}:{s:02d}'

# --- query construction ----------------------------------------------------
def build_query(lesson):
    title = lesson['lesson_title']
    module = lesson['module_title'] or ''
    # strip boilerplate words from titles
    t = re.sub(r'\(.*?\)', ' ', title)
    t = re.sub(r'[^a-zA-Z0-9\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    parts = [t]
    # add disambiguating module keyword if title is very short/generic
    if len(tokens(t)) <= 2 and module:
        mod = re.sub(r'[^a-zA-Z0-9\s]', ' ', module)
        parts.append(mod)
    return ' '.join(parts).strip()

# --- existing curated candidates -------------------------------------------
def existing_candidates(lesson, resources):
    """Reuse already-curated video entries in the repo as candidates (still verified)."""
    out = []
    lid = lesson['lesson_id']
    keys = [lid]
    # rendered legacy lesson ids like '3.01' also key resources directly
    entry = None
    for k in keys:
        if k in resources:
            entry = resources[k]
            break
    if entry:
        v = (entry.get('video') or {})
        url = v.get('url')
        vid = extract_video_id(url) or v.get('video_id')
        if vid:
            out.append({'video_id': vid, 'title': v.get('title') or '', 'channel': v.get('channel') or '', 'source': 'repo'})
    return out

def extract_video_id(url):
    if not isinstance(url, str):
        return None
    m = re.search(r'(?:v=|youtu\.be/|/embed/|/shorts/|/live/)([A-Za-z0-9_-]{11})', url)
    if m:
        return m.group(1)
    if re.match(r'^[A-Za-z0-9_-]{11}$', url.strip()):
        return url.strip()
    return None

# --- curation --------------------------------------------------------------
def curate(lesson, resources):
    query = build_query(lesson)
    q_tokens = tokens(lesson['lesson_title'] + ' ' + (lesson['module_title'] or '') + ' ' + (lesson['lesson_goal'] or ''))

    candidates = []
    seen_ids = set()

    # 1. repo-curated candidates first
    for c in existing_candidates(lesson, resources):
        if c['video_id'] not in seen_ids:
            seen_ids.add(c['video_id'])
            candidates.append(c)

    # 2. live search candidates
    for c in search_youtube(query):
        if c['video_id'] not in seen_ids:
            seen_ids.add(c['video_id'])
            candidates.append(c)

    verified = []
    for c in candidates[:MAX_CANDIDATES_PER_LESSON + 2]:
        info = verify_watch(c['video_id'])
        title_tokens = tokens(info['title'] or c.get('title') or '')
        score = overlap_score(q_tokens, title_tokens)
        # prefer shorter videos slightly; prefer educational-looking channels
        dur = info['duration_seconds'] or 0
        brevity = 0.05 * (1 - min(dur, MAX_SECONDS) / MAX_SECONDS)
        verified.append({
            'video_id': info['video_id'],
            'url': info['checked_url'],
            'title': info['title'] or c.get('title'),
            'channel': info['channel'] or c.get('channel'),
            'duration_seconds': info['duration_seconds'],
            'duration_mmss': info['duration_mmss'],
            'within_3_20min': info['within_3_20min'],
            'playability': info['playability'],
            'is_live': info['is_live'],
            'is_private': info['is_private'],
            'is_unlisted': info['is_unlisted'],
            'playable_in_embed': info.get('playable_in_embed'),
            'age_restricted': info.get('age_restricted'),
            'ok': info['ok'],
            'origin': c.get('source'),
            'relevance_score': round(score + brevity, 4),
            'relevance_raw': score,
            'verified_at': info['verified_at'],
        })

    ok = [v for v in verified if v['ok']]
    ok.sort(key=lambda v: (v['relevance_score'], -(v['duration_seconds'] or 0)), reverse=True)

    pick = ok[0] if ok else None
    # confidence heuristic
    if pick is None:
        confidence = 'NONE'
    elif pick['origin'] == 'repo':
        confidence = 'HIGH' if pick['relevance_raw'] >= 0.15 else 'MEDIUM'
    elif pick['relevance_raw'] >= 0.30:
        confidence = 'HIGH'
    elif pick['relevance_raw'] >= 0.12:
        confidence = 'MEDIUM'
    else:
        confidence = 'LOW'

    return {
        **lesson,
        'search_query': query,
        'candidates_checked': len(verified),
        'match_confidence': confidence,
        'video': pick,
        'alternates': [v for v in ok[1:3]],
        'all_verified': verified,
    }

def main():
    with open(INVENTORY, encoding='utf-8') as fh:
        inventory = json.load(fh)
    with open(RESOURCES, encoding='utf-8') as fh:
        resources = json.load(fh)

    results = []
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for i, lesson in enumerate(inventory, 1):
        if only and only not in (lesson['lesson_id'], lesson['pathway_id'], lesson['module_id']):
            continue
        rec = curate(lesson, resources)
        results.append(rec)
        v = rec['video']
        tag = f"{rec['match_confidence']:7s}"
        info = f"{v['duration_mmss']:>7s} {v['url']}" if v else 'NO_MATCH'
        print(f"[{i:3d}/{len(inventory)}] {tag} {lesson['lesson_id']:24s} {lesson['lesson_title'][:45]:45s} {info}", flush=True)

    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)

    # stats
    from collections import Counter
    conf = Counter(r['match_confidence'] for r in results)
    print('---')
    print('confidence:', dict(conf))
    print('total', len(results), 'with_video', sum(1 for r in results if r['video']))

if __name__ == '__main__':
    main()
