# Curriculum Review — Beginner Prerequisite Coverage

## Goal
Determine whether the RUACH course thoroughly teaches — from zero, for an
absolute beginner — the prerequisites later modules assume, then implement the
accepted fixes. Keep this file until the implementation is accepted.

## Verdict (delivered)
The software-engineering prerequisite chain is thorough and beginner-safe
(Module 0 starts from a literal first Python program; every lesson declares
prerequisites; cross-module deps are met before use). The weak spot is
quantitative literacy: percentiles/p99/mean, vector math (cosine, dot product),
and a `numpy` example are used before (or without) being taught.

## Implemented (2026-10-30) — audit green, 213 lessons, 0 errors
1. New primer lesson **1.00 "Reading numbers: averages, percentiles, and
   cost"** as first Module 1 lesson (stdlib only). Renumbered M1 "of 17"→"of
   18". Bumped total_lessons 212→213, module 01 lesson_count 17→18,
   config `curriculum_days` 212→213, course description, two 212 test asserts.
   Added curated beginner intro in lesson_extras.json (plain-language layer
   stays intact).
2. **M3 3.02 "How LLMs Work"** — replaced the `import numpy` softmax/attention
   snippet (code field + pages CODE block) with pure stdlib `math`.
3. **M5 5.04 "Embeddings"** — plain dot-product/cosine parenthetical added to
   the "Meaning as geometry" concept (heading count unchanged → in-scope extras
   sync preserved) + enriched the beginner `plain` text.
4. **M1 1.11 "Environment variables"** — one-line "regular expressions =
   pattern strings" gloss at the regex mention.

## Necessary collateral fix
`app/__init__.py gate_post_setup` used `current_user` without importing it — a
NameError that 500'd EVERY authenticated non-API request on this branch. Added
`current_user` to the flask_login import (strict fix; the app cannot run without it).

## OPEN DECISION (not part of the curriculum ask)
The onboarding gate is unfinished work on migrate/render (absent on main). With
the crash fixed, the gate now behaves as coded — redirecting every new
(non-onboarded) learner to /onboarding — which breaks 49 pre-existing tests
that register then navigate (profile, security, account recovery, integrations,
community, practice, dashboard flows). Options: (a) narrow the gate so
account/security/support/credential routes are never blocked, (b) have the
affected tests complete/skip onboarding in setup, or (c) hand the gate back to
its feature owner.

## Status
Curriculum work COMPLETE. Awaiting user decision on the onboarding-gate cleanup.
