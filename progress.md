# Comprehensive Performance Optimization Plan & Progress

Last updated: 2026-11-17

This document outlines the top ten architectural and code-level recommendations identified during the whole-app performance scan, alongside the real-time implementation status for each recommendation.

---

## Top Ten Performance Recommendations & Status Scorecard

| # | Optimization Area | Impact / Bottleneck | Target Outcome | Status |
|---|-------------------|---------------------|----------------|--------|
| **1** | **Eliminate N+1 Queries in `study_recalibration`** | `LessonCompletion` queried per lesson inside loop (40–80 queries per page view) | 1 batch query; reduces latency by 500–1200ms on remote DB | 🔄 In Progress |
| **2** | **Fix Gunicorn Worker Starvation in SSE Execution Stream** | `time.sleep(0.1)` loop in `stream_execution` ties up WSGI worker threads for 30s | Non-blocking/adaptive polling; eliminates worker thread starvation | ⏳ Pending |
| **3** | **Deduplicate & Memoize Request Context Queries** | `ReviewItem` queried 3x per request, `CoursePlan` queried repeatedly | Request-scoped caching in `flask.g`; eliminates 3–5 redundant DB roundtrips | ⏳ Pending |
| **4** | **Optimize Static Assets & Logo Payload** | `ruachai.png` is 1.3 MB (1254x1254) for a 40x40 icon; Pyodide 14 MB on Gunicorn | 99% reduction in logo size (~15KB); long-lived immutable cache headers | ⏳ Pending |
| **5** | **Enable JS Bundle Minification & HTTP Response Compression** | `esbuild` bundles (~910 KB each) unminified; no Gzip/Brotli on Flask/Gunicorn | Minify via `esbuild` (-50%); enable gzip compression (-75% text payload) | ⏳ Pending |
| **6** | **Eliminate Recurrent 5-Minute Curriculum JSON Re-Parsing** | 6.7 MB JSON parsed + regex processed every 300s, spiking CPU by 120–800ms | Cache curriculum permanently for process lifetime; eliminate recurrent freeze | ⏳ Pending |
| **7** | **Add Missing Database Indexes on Frequently Filtered Keys** | Missing indexes on `progress.user_id`, `(learner_id, status)`, `(user_id, skill_id)` | Fast index seeks; eliminates sequential scans on user progress tables | ⏳ Pending |
| **8** | **Bound & Decouple Blocking External CI/AI Operations** | Synchronous GitHub check scraping and Gemini rubric calls block request threads | Strict request timeouts, safe fallbacks, and decoupled job tracking | ⏳ Pending |
| **9** | **Right-Size Connection Pooling for Neon Postgres Limits** | Render configured with pool 5 + overflow 10 = 30 connections (exceeds Neon 20 limit) | Set pool=2, overflow=2 (max 8 connections); prevents pool exhaustion errors | ⏳ Pending |
| **10** | **Optimize AI Response Caching & Redis Configuration** | Unconfigured `REDIS_URL` in production wipes cache on instance sleep/recycle | Shared Redis connection support + resilient $O(1)$ in-memory fallback | ⏳ Pending |

---

## Detailed Implementation Log

### Recommendation 1: Eliminate N+1 Queries in `study_recalibration`
- **Location**: `app/learning.py` (`study_recalibration`)
- **Action**: Replace loop-bound `LessonCompletion.query.filter_by(user_id=uq, lesson_id=lesson_id).first()` with a single batch `IN` query over relevant lesson IDs. Index results in-memory.

---
*(Log will be updated as each optimization is applied and verified)*
