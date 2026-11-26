"""Repair pass for NO_MATCH lessons with improved queries + full re-verification."""
import json
import os
import re
import time

import curate_videos as CV

BASE = CV.BASE
CURATED = CV.OUT

def simplify_title(title):
    t = re.sub(r'\(.*?\)', ' ', title)
    t = re.sub(r'[^a-zA-Z0-9\s]', ' ', t)
    # drop leading 'Phase N', numbering, 'MCP', etc noise
    t = re.sub(r'\b(phase|module|lesson|part|chapter|step)\s*\d+\b', ' ', t, flags=re.I)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def query_variants(lesson):
    title = simplify_title(lesson['lesson_title'])
    module = simplify_title(lesson['module_title'] or '')
    goal = simplify_title((lesson.get('lesson_goal') or '')[:80])
    variants = []
    base = title
    if module:
        variants.append(f'{title} {module}')
    variants.append(title)
    if goal:
        variants.append(f'{title} {goal}')
    if module:
        variants.append(f'{module} {title}')
    # also a keyword-only reduction
    kt = ' '.join(CV.tokens(title)[:6])
    if kt and kt.lower() != title.lower():
        variants.append(kt + (f' {module}' if module else ''))
    # de-dup preserving order
    seen = set(); out = []
    for v in variants:
        v = re.sub(r'\s+', ' ', v).strip()
        if v and v.lower() not in seen:
            seen.add(v.lower()); out.append(v)
    return out

def verify(video_id, force=False):
    if force:
        CV.WATCH_CACHE_D.pop(video_id, None)
    info = CV.verify_watch(video_id)
    # retry once on transient failure
    if not info['ok'] and info.get('playability') not in ('OK', None):
        CV.WATCH_CACHE_D.pop(video_id, None)
        time.sleep(0.8)
        info = CV.verify_watch(video_id)
    return info

def main():
    with open(CURATED, encoding='utf-8') as fh:
        curated = json.load(fh)

    # clear cached failures so transient UNPLAYABLEs are retried
    for k in [k for k, v in CV.WATCH_CACHE_D.items() if not v.get('ok')]:
        CV.WATCH_CACHE_D.pop(k, None)
    CV._save(CV.WATCH_CACHE, CV.WATCH_CACHE_D)

    resources = CV._load(CV.RESOURCES)

    targets = [l for l in curated if l['match_confidence'] == 'NONE']
    print(f'repairing {len(targets)} NO_MATCH lessons')

    for n, lesson in enumerate(targets, 1):
        q_tokens = CV.tokens(lesson['lesson_title'] + ' ' + (lesson['module_title'] or '') + ' ' + (lesson.get('lesson_goal') or ''))
        seen_ids = set()
        candidates = []
        # repo candidate
        for c in CV.existing_candidates(lesson, resources):
            if c['video_id'] not in seen_ids:
                seen_ids.add(c['video_id']); candidates.append(c)
        # try query variants
        for q in query_variants(lesson):
            for c in CV.search_youtube(q):
                if c['video_id'] not in seen_ids:
                    seen_ids.add(c['video_id']); candidates.append(c)
            if len(candidates) >= 16:
                break

        verified = []
        for c in candidates[:18]:
            info = verify(c['video_id'], force=False)
            score = CV.overlap_score(q_tokens, CV.tokens(info['title'] or c.get('title') or ''))
            dur = info['duration_seconds'] or 0
            brevity = 0.05 * (1 - min(dur, CV.MAX_SECONDS) / CV.MAX_SECONDS)
            verified.append({
                'video_id': info['video_id'], 'url': info['checked_url'],
                'title': info['title'] or c.get('title'), 'channel': info['channel'] or c.get('channel'),
                'duration_seconds': info['duration_seconds'], 'duration_mmss': info['duration_mmss'],
                'within_3_20min': info['within_3_20min'], 'playability': info['playability'],
                'is_live': info['is_live'], 'is_private': info['is_private'], 'is_unlisted': info['is_unlisted'],
                'playable_in_embed': info.get('playable_in_embed'), 'age_restricted': info.get('age_restricted'),
                'ok': info['ok'], 'origin': c.get('source'), 'relevance_score': round(score + brevity, 4),
                'relevance_raw': score, 'verified_at': info['verified_at'],
            })

        ok = [v for v in verified if v['ok']]
        ok.sort(key=lambda v: (v['relevance_score'], -(v['duration_seconds'] or 0)), reverse=True)
        pick = ok[0] if ok else None
        if pick is None:
            conf = 'NONE'
        elif pick['origin'] == 'repo':
            conf = 'HIGH' if pick['relevance_raw'] >= 0.15 else 'MEDIUM'
        elif pick['relevance_raw'] >= 0.30:
            conf = 'HIGH'
        elif pick['relevance_raw'] >= 0.12:
            conf = 'MEDIUM'
        else:
            conf = 'LOW'

        lesson['candidates_checked'] = len(verified)
        lesson['match_confidence'] = conf
        lesson['video'] = pick
        lesson['alternates'] = ok[1:3]
        lesson['all_verified'] = verified
        if pick is None:
            lesson['search_query'] = query_variants(lesson)[0]
        else:
            lesson['search_query'] = query_variants(lesson)[0]

        info = f"{pick['duration_mmss']} {pick['url']}" if pick else 'STILL NO_MATCH'
        print(f"[{n}/{len(targets)}] {conf:7s} {lesson['lesson_id']:22s} {lesson['lesson_title'][:42]:42s} {info}", flush=True)

    with open(CURATED, 'w', encoding='utf-8') as fh:
        json.dump(curated, fh, ensure_ascii=False, indent=1)

    from collections import Counter
    conf = Counter(l['match_confidence'] for l in curated)
    print('confidence:', dict(conf))
    print('with_video', sum(1 for l in curated if l['video']), 'total', len(curated))

if __name__ == '__main__':
    main()
