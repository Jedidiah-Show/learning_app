"""Re-query LOW-confidence picks with goal-augmented variants and stricter relevance."""
import json
import re

import curate_videos as CV

CURATED = CV.OUT
MIN_REL = 0.12

def kw(text, n=8):
    return ' '.join(CV.tokens(text)[:n])

def query_variants(lesson):
    title = re.sub(r'[^a-zA-Z0-9\s]', ' ', lesson['lesson_title'])
    title = re.sub(r'\b(phase|module|lesson)\s*\d+\b', ' ', title, flags=re.I).strip()
    title = re.sub(r'\s+', ' ', title)
    module = re.sub(r'[^a-zA-Z0-9\s]', ' ', lesson['module_title'] or '').strip()
    goal = (lesson.get('lesson_goal') or '').strip()
    variants = []
    if goal:
        variants.append(f'{title} {kw(goal, 6)}')
    variants.append(title)
    if module:
        variants.append(f'{title} {module}')
    if goal:
        variants.append(kw(goal, 8))
    # de-dup
    seen=set(); out=[]
    for v in variants:
        v=re.sub(r'\s+',' ',v).strip()
        if v and v.lower() not in seen:
            seen.add(v.lower()); out.append(v)
    return out

def main():
    curated = CV._load(CURATED)
    targets = [l for l in curated if l['match_confidence'] == 'LOW']
    print('LOW targets', len(targets))

    for n, lesson in enumerate(targets, 1):
        q_tokens = CV.tokens(' '.join([lesson['lesson_title'], lesson['module_title'] or '', lesson.get('lesson_goal') or '']))
        seen=set(); candidates=[]
        for c in CV.existing_candidates(lesson, CV._load(CV.RESOURCES)):
            if c['video_id'] not in seen: seen.add(c['video_id']); candidates.append(c)
        for q in query_variants(lesson):
            for c in CV.search_youtube(q):
                if c['video_id'] not in seen: seen.add(c['video_id']); candidates.append(c)
            if len(candidates) >= 18: break

        verified=[]
        for c in candidates[:20]:
            info = CV.verify_watch(c['video_id'])
            score = CV.overlap_score(q_tokens, CV.tokens(info['title'] or c.get('title') or ''))
            dur = info['duration_seconds'] or 0
            brevity = 0.05*(1-min(dur,CV.MAX_SECONDS)/CV.MAX_SECONDS)
            verified.append({
                'video_id': info['video_id'],'url': info['checked_url'],'title': info['title'] or c.get('title'),
                'channel': info['channel'] or c.get('channel'),'duration_seconds': info['duration_seconds'],
                'duration_mmss': info['duration_mmss'],'within_3_20min': info['within_3_20min'],'playability': info['playability'],
                'is_live': info['is_live'],'is_private': info['is_private'],'is_unlisted': info['is_unlisted'],
                'playable_in_embed': info.get('playable_in_embed'),'age_restricted': info.get('age_restricted'),'ok': info['ok'],
                'origin': c.get('source'),'relevance_score': round(score+brevity,4),'relevance_raw': score,'verified_at': info['verified_at']})

        ok=[v for v in verified if v['ok']]
        ok.sort(key=lambda v:(v['relevance_score'],-(v['duration_seconds'] or 0)),reverse=True)
        pick=ok[0] if ok else None
        # keep existing pick if new pick isn't strictly better
        existing=lesson['video']
        existing_rel = existing.get('relevance_raw') or 0
        if pick and (not existing or pick['relevance_score'] >= (existing.get('relevance_score') or 0) or existing_rel < MIN_REL):
            chosen=pick
        else:
            chosen=existing
        # confidence
        rel = (chosen or {}).get('relevance_raw') or 0
        if chosen is None: conf='NONE'
        elif rel >= 0.30: conf='HIGH'
        elif rel >= 0.12: conf='MEDIUM'
        else: conf='LOW'
        lesson['match_confidence']=conf
        lesson['video']=chosen
        lesson['alternates']=ok[1:3]
        lesson['all_verified']=verified
        print(f"[{n}/{len(targets)}] {conf:7s} {lesson['lesson_id']:20s} rel={rel:.3f} {(chosen or {}).get('title','NO_MATCH')[:60]}", flush=True)

    CV._save(CURATED, curated)
    from collections import Counter
    print(dict(Counter(l['match_confidence'] for l in curated)))

if __name__=='__main__':
    main()
