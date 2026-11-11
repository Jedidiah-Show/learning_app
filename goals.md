# RUACH Platform — Release Goals & Objectives

## Executive Summary
This document defines the strategic product goals, measurable targets, and core acceptance criteria for the **RUACH Learning & Engineering Growth Release**. 

The goal of this release is to transition RUACH from a lesson-focused content delivery platform into an integrated learning, practice, and skill verification engine.

---

## Strategic Goals

### Goal 1: Establish High-Integrity Coding & AI Engineering Practice
*   **Objective:** Transform RUACH practice into an interactive, multi-track coding experience ("Practice Arena") featuring both algorithmic foundations and practical AI engineering.
*   **Target:** 
    *   Deploy a two-track catalogue (AI Engineering & Algorithms/DSA).
    *   Implement isolated server-side submission execution with hidden test cases.
    *   Ensure 0% client-side inspection leakage for hidden test logic and evaluation scripts.

### Goal 2: Evidence-Based Skill Verification (Skill Passport)
*   **Objective:** Replace passive lesson completion metrics with a verified Skill Passport that reflects demonstrated competence.
*   **Target:**
    *   Map 100% of curriculum lessons and Practice Arena problems to specific competency nodes.
    *   Provide real-time learner competency state tracking (Not Started, Developing, Demonstrated, Mastered) based on verified submission data.

### Goal 3: Conversational & Context-Aware Instructional Guidance (AI Tutor 2.0)
*   **Objective:** Upgrade the AI Tutor into an instructional companion that diagnoses knowledge gaps rather than just answering questions.
*   **Target:**
    *   Achieve context-awareness (curriculum position, code attempts, error logs, skill passport state).
    *   Deploy a progressive 5-stage hinting engine for practice and project troubleshooting.
    *   Maintain tutor response latency $< 1.5$ seconds for first-byte streaming.

### Goal 4: Project-Based Engineering Mastery (Project Studio)
*   **Objective:** Introduce end-to-end guided projects that validate system building capability (APIs, RAG pipelines, model deployment, monitoring).
*   **Target:**
    *   Launch 2 flagship AI Engineering projects with automated milestone verification and GitHub evidence submission.

### Goal 5: Hardened Platform Trust, Security & Observability
*   **Objective:** Resolve outstanding security, environment isolation, and workflow verification items prior to public release.
*   **Target:**
    *   Achieve 100% resolution on CSRF, DNS-rebinding, SSRF, and isolated code execution security boundaries.
    *   Sustain $> 99.5\%$ automated test suite pass rate across backend, frontend, and browser integration layers.

---

## Key Performance Indicators (KPIs)

| Metric Category | Target Indicator | Baseline | Success Target |
| :--- | :--- | :--- | :--- |
| **Engagement** | Practice Problem Completion | 62 Pyodide-only client exercises | 50+ Server-verified problems across 2 tracks |
| **Accuracy** | Code Execution Security Integrity | Client-side check inspection possible | Zero untrusted code execution on host server |
| **Pedagogy** | Socratic Hint Conversion Rate | Single-stage/Static worked solution | $\ge 65\%$ resolution via progressive hints without revealing solution |
| **Completeness** | Skill Passport Coverage | Page view / lesson click completion | 100% evidence-backed capability tracking |

---

## Core Acceptance Criteria

1. **Practice Arena:**
   - Dual track navigation: **AI Engineering** (Flagship) and **Algorithms & Problem Solving**.
   - Dual execution paths: In-browser fast feedback (**Run** via Pyodide) and authoritative server-side judging (**Submit** via containerized sandbox).
   - Standardized problem schema with progressive hint stages, editorials, and complexity analysis.

2. **Skill Passport:**
   - Granular competence nodes dynamically driven by project submissions and problem verdicts.
   - Learner-facing skill radar and downloadable verification summary.

3. **AI Tutor 2.0:**
   - Memory and context awareness spanning execution errors, recent submissions, and current lesson context.
   - Socratic prompt guardrails preventing immediate code copy-pasting solutions during practice mode.

4. **Project Studio:**
   - Guided multi-milestone project workflows with automated assertion testing and repo validation.

5. **Security & Infrastructure:**
   - Secure execution engine running untrusted code with CPU, memory, network isolation, and strict time limits.
   - Hardened API endpoints with CSRF, SSRF, and rate-limiting protections.