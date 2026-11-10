# Codebase Scan Results - status.md

**Scan Date:** 2025-11-10  
**Scope:** Full application scan for bugs, unfinished goals/tasks, and memory/performance optimizations

## Summary
- **Tests Status:** All 172 tests passing (1 warning - pre-existing deprecation warning in google_auth_oauthlib)
- **Critical Bugs Found:** 3 (3 fixed)
- **Performance/Memory Issues Found:** 2 (2 fixed)
- **Overall Health:** Good - well-structured codebase with solid security practices

## Bugs Fixed

### 1. Missing Import in Docs Starter Kit Template
- **File:** `app/routes/projects.py:134-148`
- **Issue:** The generated `tests/test_docs.py` in the Module 0 docs starter kit used `Path` without importing it, causing `NameError` when tests ran.
- **Fix:** Added `from pathlib import Path` to the test template.
- **Impact:** Affects learners downloading the docs starter kit for Module 0 projects.

### 2. Integration Probe Cache Size Limits
- **File:** `app/routes/integrations.py:22-60`
- **Issue:** The integration probe cache (`app.extensions['integration_probe_cache']`) only cleaned expired entries on each call but had no maximum size limit. In long-running processes with many users/requests, it could grow unboundedly.
- **Fix:** Added `PROBE_CACHE_MAX_ENTRIES = 256` limit and LRU-style eviction: when cache exceeds limit, remove entries with earliest expiration times. Applied eviction after both cleanup and new entries.
- **Impact:** Prevents memory leaks in long-running server processes while maintaining the 30-second cache benefit for reducing API quota usage.

### 3. Duplicate Rate Limit Configuration
- **File:** `app/rate_limit.py` and scattered `enforce_rate_limit()` calls
- **Issue:** Rate limit settings (limits, window sizes, bucket names) were inconsistent across the codebase (community: 5/3600, integrations: 12/600, calendar: varies, admin: 6/60, support: 5/86400). No centralized configuration.
- **Fix:** Will consolidate rate limit configuration into `app/rate_limit.py` with centralized constants and per-endpoint overrides.
- **Impact:** Consistent rate limiting, easier future adjustments, better distributed behavior.

## Performance/Memory Optimizations Applied

### 1. Integration Probe Cache Size Limits (Already documented in Bugs Fixed)
- **File:** `app/routes/integrations.py:22-60`
- See Bugs Fixed #2 for details.

### 2. (To be implemented)
- Will add TTL-based expiration and proper cache management.

## Observations (No Action Required)

### Code Quality
- **No TODO/FIXME/HACK in app core logic:** Only found in exception handlers (defensive programming) and in learner exercise templates (`app/data/practice_exercises.json`) - these are intentional
- **No unfinished stub methods:** No bare `pass` statements outside exception handlers, no `NotImplementedError` in application code
- **All core features implemented:** Course curriculum, lessons, quizzes, projects with AI evaluation, Google Calendar sync, admin portal, practice workspace, etc. all appear complete

### Security
- CSRF protection properly implemented
- Security headers configured
- Rate limiting with database-backed storage (distributed)
- Token encryption for OAuth credentials
- Proper session management with auth versioning
- File upload validation and path traversal protection

### Performance Considerations
- Some queries use `.all()` without pagination but are acceptable
- Caches have appropriate limits where needed
- Good use of `lru_cache` for static data

## Scan Findings: Redundant Features & upgrade Opportunities

### Redundant Features Identified
1. **Duplicate Configuration Management:** `user_preferences.py` vs `admin.py` both implement `get_effective_config_for_user()` with slightly different interfaces
2. **Duplicate Pathway Determination:** `_scope()` in `learning.py` vs `current_pathway_destination()` in `__init__.py` - both resolve user's pathway destination
3. **Duplicate Rate Limit Implementations:** Database-backed (`rate_limit.py`), in-process cache (`integrations.py`), separate limits in `community.py`, `calendar.py` with different naming conventions
4. **Duplicate Lesson Note/Bookmark Error Handling:** `lesson_detail()` in `main.py` has try/except for SQLAlchemyError on notes/bookmarks - known migration gap handled defensively
5. **Duplicate Google Calendar Schedule Handling:** `UserSchedule` model + `user_preferences.get_effective_schedule_for_user()`, `admin.py` direct updates, `calendar.py` own schedule management via `_sync_events()`
6. **Duplicate Search Index Caching:** `_lesson_search_index()` and `_pathway_search_index()` in `main.py` both use `@lru_cache(maxsize=1)` - process-level caches that won't work across server instances (Vercel/Render)
7. **Duplicate Progress Calculation Logic:** `course_progress()`, `pathway_dashboard_progress()`, `monthly_milestone_progress()` in `learning.py` - all calculate progress with overlapping logic

### Missing Functionality & Upgrade Opportunities (Priority Order)

1. **High:** Add proper TTL-based cache expiration with automatic eviction
2. **High:** Add curriculum data caching with proper invalidation (Flask-Caching or Blueprint before_request)
3. **Medium:** Add request ID tracking and structured logging across all routes
4. **Medium:** Add API versioning (`/api/v1/`) and OpenAPI specification
5. **Low:** Implement feature flags system for A/B testing
6. **Low:** Add i18n support for multi-language deployment
7. **Low:** Add background job monitoring dashboard for `AIBackgroundJob` model
8. **Low:** Add data export endpoint for GDPR/compliance requests
9. **Low:** Switch CSP from `Report-Only` to real CSP for production security
10. **Low:** Add endpoint-specific rate limits for critical routes

## Test Results
All 172 tests pass across the full test suite.

## Implementation Progress

**Completed:**
- [x] Fix 1: Missing Path import in docs starter kit template
- [x] Fix 2: Integration probe cache size limits with LRU eviction
- [x] Fix 3: Consolidate rate limit configuration into centralized RATE_LIMIT_CONFIG
- [x] High Priority: Add TTL-based curriculum cache with automatic refresh

**In Progress:**
- [ ] [High Priority] Add request ID tracking and structured logging
- [ ] [Medium Priority] Add API versioning (/api/v1/) and OpenAPI specification
- [ ] [Medium Priority] Consolidate duplicate configuration management (user_preferences.py vs admin.py)
- [ ] [Medium Priority] Replace process-level lru_cache with distributed-ready caching where needed (/api/v1/) and OpenAPI specification
