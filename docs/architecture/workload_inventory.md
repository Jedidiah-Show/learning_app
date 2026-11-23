# RUACH LMS — Workload Inventory & Execution Tiers (M0 Audit)

**Date:** 2026-11-24  
**Release:** Architecture Evolution 1.0  
**Baseline Commit:** `41d1d16`

---

## 1. Workload Categorization

RUACH workloads are categorized into four distinct execution tiers to protect the web application from latency spikes and security risks.

```
                           WORKLOAD CLASSIFICATION
                                     |
    +-----------------+--------------+---------------+-----------------+
    |                 |                              |                 |
    v                 v                              v                 v
[ Tier 1: Client ] [ Tier 2: Sync Web ]    [ Tier 3: Async Queue ] [ Tier 4: Container Judge ]
Pyodide in-browser  Auth, lesson read,      AI document ingest,      Coding arena runs,
CodeMirror editing  quiz check, metadata    RAG embedding, eval      isolated tests
```

---

## 2. Workload Matrix

| Workload Type | Execution Tier | Execution Host | Typical Latency | Failure Blast Radius | Concurrency & Limits |
|---|---|---|---|---|---|
| **Browsing & Navigation** | Sync Request | Web (Gunicorn/Flask) | 20–80 ms | Single HTTP request | Bounded by DB pool (2+2 connections per worker) |
| **Lesson Quiz Grading** | Sync Request | Web (Gunicorn/Flask) | 30–100 ms | Single HTTP request | Deterministic Python check |
| **Interactive Tutor (Chat)** | Sync Request | Web calling Gemini/OpenRouter | 800–2500 ms | Web thread blocked | Strict 12s timeout; fallback provider |
| **Client Code Execution** | Client Runtime | Learner Browser (Pyodide 0.26) | Instant (Client CPU) | Learner browser tab | Web process completely untouched |
| **AI Document Ingestion** | Async Job | AI Worker (`ai_worker.py`) | 5–60 s | Background job retry | Bounded job queue (`ai_background_job`) |
| **AI Project Review / Eval**| Async Job | AI Worker (`ai_worker.py`) | 10–90 s | Background job retry | Lease timeout (300s); max retries 3 |
| **Arena Code Execution** | Isolated Container | Judge Worker (`judge_worker.py`)| 1–10 s | Sandbox container | Clamped CPU (1.0), RAM (256MB), rlimit |
| **Queue Maintenance** | Scheduled Pass | Scheduler (`scheduler.py`) | 50–200 ms | Stale lease reclaim | Single scheduler lock |

---

## 3. Execution Profiles Registry (`app/execution/profiles.py`)

Workloads submitted to execution workers are bounded by server-enforced profiles:

1. **`browser_python`**
   * Runtime: In-browser WebAssembly (Pyodide).
   * Memory Limit: Bounded by client browser.
   * Network: Disabled (browser sandbox).
2. **`container_python`**
   * Runtime: Docker container (`ruach-python-sandbox:3.12-v1`).
   * Limits: 1.0 vCPU, 256 MB RAM, 10s execution timeout, 50 processes.
   * Network: Completely disabled (`--network none`).
   * Filesystem: Read-only root filesystem with restricted 10MB writable tmpfs.
3. **`container_data_science`**
   * Runtime: Docker container with `numpy`, `pandas`, `scipy`, `scikit-learn`, `matplotlib`.
   * Limits: 1.0 vCPU, 512 MB RAM, 20s execution timeout.
   * Network: Disabled.
4. **`container_ml`**
   * Status: Declared; gated behind dedicated ML worker deployment.
   * Limits: 2.0 vCPU, 1024 MB RAM, 60s execution timeout.
5. **`gpu_training`**
   * Status: Declared; disabled until managed GPU infrastructure is connected.
