# RUACH Platform — Release Milestones & Phase Map

## Release Overview
The **RUACH Learning & Engineering Growth Release** is structured into 7 sequential phases (M0 through M6). Each milestone contains defined deliverables, target completion criteria, and mandatory release gates.

---

## Phase Breakdown

```
[M0: Spec & Security Hardening] ➔ [M1: Practice Arena Experience] ➔ [M2: Workspace & Execution]
                                                                            │
[M6: Launch & Verification] ◄── [M5: Learning Intelligence] ◄── [M4: Project Studio & Labs] ◄── [M3: Sandbox Judge Engine]
```

---

### Milestone 0: Core Foundation, Security Hardening & Specifications (P0)
**Goal:** Establish specifications, eliminate security vulnerabilities, and harden existing infrastructure.

*   [ ] **M0.1 Technical Specifications:** Finalize schemas for Practice Arena, Skill Passport, AI Tutor 2.0, and Project Studio.
*   [ ] **M0.2 Security Hardening:**
    *   Implement comprehensive SSRF prevention filters on external request workers.
    *   Validate CSRF token verification across all write/mutation routes.
    *   Harden DNS-rebinding protection on local/internal services.
*   [ ] **M0.3 Project Verification Fixes:** Address GitHub verification flow boundary edge-cases and API error handles.
*   [ ] **Exit Gate:** 100% security issue resolution; security review sign-off.

---

### Milestone 1: Practice Arena Experience & Catalog (P0)
**Goal:** Redesign the practice interface to support dual-track navigation and catalog exploration.

*   [ ] **M1.1 Dual-Track Navigation:** Implement UI filters for **AI Engineering** (Flagship) and **Algorithms & DSA**.
*   [ ] **M1.2 Problem Discovery:** Problem search, skill tag filtering, difficulty badges (Easy, Medium, Hard), and completion status flags.
*   [ ] **M1.3 Content Migration:** Re-structure the existing 62 Python exercises into the new versioned problem schema.
*   [ ] **Exit Gate:** Functional catalogue rendering both tracks with full search and filter support.

---

### Milestone 2: Coding Workspace & Client-Side Execution (P1)
**Goal:** Deliver a modern, split-panel coding environment with fast client-side feedback.

*   [ ] **M2.1 Workspace UI:** Build resizable, split-pane CodeMirror editor layout with full-screen, dark/light themes, and shortcut bindings.
*   [ ] **M2.2 Client-Side Pyodide Integration:** Refactor Pyodide sandbox for fast local testing (**Run** path) with custom test inputs.
*   [ ] **M2.3 State Persistence:** Implement local and backend autosave for draft code per problem per user.
*   [ ] **Exit Gate:** Responsive workspace running local tests via Pyodide with draft persistence.

---

### Milestone 3: Secure Server-Side Python Judge Infrastructure (P0)
**Goal:** Build an isolated, secure server-side execution engine for authoritative submission testing (**Submit** path).

*   [ ] **M3.1 Containerized Execution Engine:** Deploy lightweight, isolated execution sandboxes (gVisor / Docker / nsjail) with resource constraints:
    *   Execution timeout: $\le 5.0$ seconds.
    *   Memory limit: $\le 256$ MB.
    *   Network access: Disabled.
*   [ ] **M3.2 Submission Queue & Result Parser:** Asynchronous task queue (Celery/Redis or lightweight worker) for verdict evaluation:
    *   `Accepted`, `Wrong Answer`, `Time Limit Exceeded`, `Memory Limit Exceeded`, `Runtime Error`.
*   [ ] **M3.3 Hidden Test Evaluation:** Secure storage and server-side execution of hidden test suites.
*   [ ] **Exit Gate:** Reliable execution of untrusted user code with zero host system privilege escalation leakage.

---

### Milestone 4: Learning Path, Skill Passport & Project Studio (P1)
**Goal:** Connect problem solving, lesson completion, and projects to demonstrated skills.

*   [ ] **M4.1 Skill Passport Engine:** Build skill node dependency graph linking curriculum, practice problems, and projects.
*   [ ] **M4.2 Learner Passport Dashboard:** Interactive skill map showing demonstrated vs developing competencies.
*   [ ] **M4.3 Project Studio Foundation:** Launch first 2 guided AI Engineering projects:
    *   *Project A:* Build a Validated REST API Service.
    *   *Project B:* Build an End-to-End RAG Document Retriever.
*   [ ] **M4.4 Project Milestone Verifier:** Automated assertions verifying milestone deliverables (repo verification & output checks).
*   [ ] **Exit Gate:** Verified competency updates in Skill Passport upon problem/project completion.

---

### Milestone 5: AI Tutor 2.0 & Learning Intelligence (P1)
**Goal:** Upgrade the AI Tutor into a context-aware instructional companion.

*   [ ] **M5.1 Context Injector:** Feed user submission history, current code diffs, execution errors, and passport state into tutor context window.
*   [ ] **M5.2 Socratic Guidance Engine:** Implement prompt rules forcing step-by-step troubleshooting assistance rather than raw solution output.
*   [ ] **M5.3 Progressive Hint System:** 5-stage progressive reveal (1. Concept $\rightarrow$ 2. Approach $\rightarrow$ 3. Edge cases $\rightarrow$ 4. Pseudocode $\rightarrow$ 5. Editorial).
*   [ ] **Exit Gate:** Tutor accurately diagnoses sample code bugs in test scenarios without outputting full direct solutions prematurely.

---

### Milestone 6: Platform Verification, Engineering Labs & Release (P0)
**Goal:** End-to-end integration testing, smoke testing, performance validation, and deployment.

*   [ ] **M6.1 Engineering Labs (Pilot):** Deploy initial debugging lab ("Diagnose and Fix Broken Model API Client").
*   [ ] **M6.2 E2E & Browser Testing:** Run full regression suite ($>250$ tests) including Playwright/Selenium browser flows.
*   [ ] **M6.3 Smoke Testing & Migration:** Production dry-run, DB migration script verification, rollback validation.
*   [ ] **M6.4 Official Release:** Production rollout and release notes publication.
*   [ ] **Exit Gate:** Green test suites, smooth migration dry-run, zero critical bugs in staging.