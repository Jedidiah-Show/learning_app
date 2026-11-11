# RUACH Platform — Technical Implementation Plan

## Architectural Overview

The architecture introduces a decoupled **Server-Side Judging Engine**, a **Skill Graph Engine**, and an upgraded **AI Tutor Context Pipeline**, while preserving the Flask core and Pyodide client-side execution.

```
+-----------------------------------------------------------------------+
|                            Client Browser                             |
|  +-----------------------+  +--------------------------------------+  |
|  |  Pyodide Runner (Run) |  |  CodeMirror Workspace & UI Panel     |  |
|  +-----------+-----------+  +------------------+-------------------+  |
+--------------|---------------------------------|----------------------+
               |                                 | REST / WebSockets
               v                                 v
+-----------------------------------------------------------------------+
|                          RUACH Core (Flask Web API)                   |
|  +------------------+  +------------------+  +---------------------+  |
|  |  Practice Arena  |  |  Skill Passport  |  |   AI Tutor 2.0      |  |
|  |  Controller      |  |  Engine          |  |   Context Pipeline  |  |
|  +--------+---------+  +--------+---------+  +----------+----------+  |
+-----------|---------------------|-------------------------|-----------+
            | Async Task          | SQL Queries             | LLM API
            v                     v                         v
+-----------------------+ +------------------+ +------------------------+
| Isolated Judge Queue  | | SQLite / Postgres| | OpenAI / Anthropic API |
| (gVisor/Docker Runner)| | Database         | | (Socratic Guardrails)  |
+-----------------------+ +------------------+ +------------------------+
```

---

## Component Work Breakdown

### 1. Database Schema & Data Models

#### Practice Arena Models
```python
# models/practice.py
class Problem(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    slug = db.Column(db.String(128), unique=True, nullable=False)
    title = db.Column(db.String(256), nullable=False)
    track = db.Column(db.Enum('AI_ENGINEERING', 'ALGORITHMS'), nullable=False)
    difficulty = db.Column(db.Enum('EASY', 'MEDIUM', 'HARD'), nullable=False)
    statement_markdown = db.Column(db.Text, nullable=False)
    input_format = db.Column(db.Text)
    output_format = db.Column(db.Text)
    constraints = db.Column(db.Text)
    starter_code = db.Column(db.JSON)  # {"python": "def solution()..."}
    public_test_cases = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class HiddenTestCase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    problem_id = db.Column(db.String(64), db.ForeignKey('problem.id'))
    input_data = db.Column(db.Text, nullable=False)
    expected_output = db.Column(db.Text, nullable=False)
    is_secret = db.Column(db.Boolean, default=True)

class Submission(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    problem_id = db.Column(db.String(64), db.ForeignKey('problem.id'))
    language = db.Column(db.String(32), default='python')
    code_snapshot = db.Column(db.Text, nullable=False)
    verdict = db.Column(db.Enum('PENDING', 'ACCEPTED', 'WRONG_ANSWER',
                                'TIME_LIMIT_EXCEEDED', 'MEMORY_LIMIT_EXCEEDED',
                                'RUNTIME_ERROR', 'COMPILE_ERROR'), default='PENDING')
    execution_time_ms = db.Column(db.Integer)
    memory_kb = db.Column(db.Integer)
    tests_passed = db.Column(db.Integer, default=0)
    total_tests = db.Column(db.Integer, default=0)
    error_details = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
```

#### Skill Passport Models
```python
# models/passport.py
class SkillNode(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    category = db.Column(db.String(64)) # e.g., "Python", "RAG", "APIs"

class UserSkillProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    skill_id = db.Column(db.String(64), db.ForeignKey('skill_node.id'))
    status = db.Column(db.Enum('NOT_STARTED', 'DEVELOPING', 'DEMONSTRATED', 'MASTERED'))
    evidence_type = db.Column(db.String(32)) # "PROBLEM", "PROJECT", "LESSON"
    evidence_id = db.Column(db.String(64))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
```

---

### 2. Secure Server-Side Execution Engine

The judge runs submissions inside unprivileged, ephemeral containers or isolated sandboxes (gVisor / nsjail).

#### Sandbox Execution Flow
```python
# services/judge.py
import subprocess
import json

def execute_in_sandbox(code: str, test_cases: list, timeout_sec: float = 3.0) -> dict:
    """
    Executes Python code safely against hidden test cases.
    """
    payload = {
        "code": code,
        "test_cases": test_cases,
        "timeout": timeout_sec
    }

    # Run container with dropped privileges, no network, read-only rootfs
    docker_cmd = [
        "docker", "run", "--rm", "-i",
        "--network", "none",
        "--memory", "256m",
        "--cpus", "0.5",
        "--read-only",
        "--security-opt", "no-new-privileges:true",
        "ruach-python-sandbox:latest"
    ]

    try:
        proc = subprocess.run(
            docker_cmd,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=timeout_sec + 2.0
        )
        return json.loads(proc.stdout)
    except subprocess.TimeoutExpired:
        return {"verdict": "TIME_LIMIT_EXCEEDED", "tests_passed": 0}
    except Exception as e:
        return {"verdict": "INTERNAL_ERROR", "details": str(e)}
```

---

### 3. API Routes & Contracts

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/practice/problems` | List problems with search, track, and difficulty filters. |
| `GET` | `/api/v1/practice/problems/<id>` | Fetch statement, constraints, public test cases, and starter code. |
| `POST`| `/api/v1/practice/problems/<id>/submit` | Submit code for authoritative server-side judging. |
| `GET` | `/api/v1/practice/submissions/<id>` | Fetch verdict, run time, memory, test results. |
| `GET` | `/api/v1/passport` | Retrieve current user's Skill Passport progress and graph. |
| `POST`| `/api/v1/tutor/chat` | Send message to AI Tutor 2.0 with context payload. |

---

### 4. Implementation Stages & Timeline

```
Week 1 - 2: Core Hardening & Arena Spec (M0, M1)
- Security audit fixes (SSRF, CSRF, DNS rebinding).
- Database migrations for Problem, Submission, and Skill schemas.
- Practice Arena catalog interface.

Week 3 - 4: Coding Workspace & Judge Architecture (M2, M3)
- Split-pane CodeMirror workspace setup.
- Pyodide client integration for quick "Run".
- Docker/gVisor sandboxing for "Submit" execution service.

Week 5 - 6: Skill Passport & Project Studio (M4)
- Automated skill node state update triggers.
- Passport UI visualization dashboard.
- Initial 2 Project Studio project specs & assertion runners.

Week 7 - 8: AI Tutor 2.0, Testing & Release (M5, M6)
- AI Tutor context assembly (code diff + error log + skill state).
- 5-stage progressive hinting engine.
- End-to-end browser test suite run and production rollout.
```

---

## Operational Verification & Acceptance

Before approving deployment, run the verification harness:

```bash
# 1. Run Python unit & integration tests
pytest tests/ --ignore=tests/browser/ -v

# 2. Run Browser integration tests
pytest tests/browser/ -v

# 3. Test Security Execution Sandbox isolation
python scripts/test_sandbox_security.py

# 4. Validate DB Migrations
flask db upgrade && flask db check
```
