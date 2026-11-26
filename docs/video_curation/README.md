# Video Content Curation

Reproducible generator for the LMS-wide lesson → YouTube video review document
**`video_content.docx`** (repository root).

## What it produces

`video_content.docx` — organized **Pathway → Module → Lesson**. Every lesson in
every pathway is listed; nothing is skipped. Each lesson shows a curated,
**verified** YouTube video (duration **3–20 minutes**, i.e. 180–1200 s) plus
match confidence and verification details. Lessons with no qualifying video are
explicitly marked `NO_MATCH`, never silently dropped. (Current build: **382
lessons discovered across all LMS sources, 381 with a verified video, 1
NO_MATCH** — lesson `2.13` “SQL”, which has no qualifying 3–20 min YouTube
video; it is listed explicitly rather than skipped.)

## Pathways covered (every pathway in the LMS)

| Pathway | id | Source of truth |
|---|---|---|
| Shared Foundations | `shared-foundations` | `shared_foundations_curriculum.json` + `app/data/shared_foundations_lessons.json` |
| AI Engineering (canonical) | `ai-engineering` | `ai_engineering_curriculum.json` |
| AI Engineering (rendered catalog) | `ai-engineering` | `app/data/dynamoai_curriculum.json`, modules 03–12, as displayed |
| Machine Learning | `machine-learning` | `machine_learning_curriculum.json` (mirrors `app/data/machine_learning_pathway.json`, id `machine-learning-engineering`) |
| Cloud & AI Infrastructure | `cloud-ai-infrastructure` | `app/data/cloud_ai_infrastructure_pathway.json` |

See `docs/CURRICULUM_ID_MIGRATION.md` for the canonical three-domain model and
the legacy `dynamoai` → canonical mapping.

## Integrity (no assumption / skipping / deferral / hallucination)

- No video link is invented. Every link is `https://www.youtube.com/watch?v=<id>`
  for a real id.
- Every pick is verified against the **live** YouTube watch page: exists, HTTP
  200, `playabilityStatus=OK`, **not** live/private/unlisted/age-restricted,
  `playableInEmbed` not false, exact `lengthSeconds` within [180, 1200].
- Transient `UNPLAYABLE` responses are retried; failed checks are not cached.
- `match_confidence` (HIGH/MEDIUM/LOW/NONE) reflects automated title/topic
  relevance + verification; `LOW`/`NONE` rows need human review; manually
  re-selected picks are noted.
- A random + all-`LOW` + all-manual fresh re-fetch re-check passed (durations
  recorded == durations live).

## Rebuild

```bash
# 1. app venv python from repo root
# 1. app venv python from repo root
.venv/bin/python docs/video_curation/build_inventory.py
# 2. curate + verify YouTube (network required; caches written beside scripts)
.venv/bin/python docs/video_curation/curate_videos.py            # full
.venv/bin/python docs/video_curation/repair_no_match.py          # retry NONE
.venv/bin/python docs/video_curation/repair_low.py               # re-rank LOW
# 3. render docx (writes repo-root video_content.docx)
.venv/bin/python docs/video_curation/build_docx.py
```

`curated_videos.json` in this directory is the final verified dataset used for
the shipped `video_content.docx`. Caches (`cache_search.json`,
`cache_watch.json`) are written next to the scripts when run in-place.

## Files

- `build_inventory.py` — extract the complete lesson inventory from the app.
- `curate_videos.py` — YouTube search + verification + ranking.
- `repair_no_match.py` — retry `NONE` with better queries + re-verification.
- `repair_low.py` — re-query/re-rank `LOW` picks.
- `build_docx.py` — render `video_content.docx`.
- `lessons_inventory.json` — the lesson inventory.
- `curated_videos.json` — final curated + verified video per lesson.
