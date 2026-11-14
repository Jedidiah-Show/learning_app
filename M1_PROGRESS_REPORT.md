# M1 — Curriculum Separation and Shared Foundations

**Priority:** Critical  
**Purpose:** Separate the learning content into three independent curriculum domains.

---

## M1.1 — Curriculum Domain Definitions Created

Three independent curriculum definition files created:

| File | ID | Domain Type | Modules | Lessons | Objective |
|---|---|---|---|---|---|
| `shared_foundations_curriculum.json` | `shared-foundations` | FOUNDATION | 6 | N/A | Core foundations for all pathways |
| `ai_engineering_curriculum.json` | `ai-engineering` | SPECIALIZATION | 9 | 28 | AI Engineering specialisation |
| `machine_learning_curriculum.json` | `machine-learning` | SPECIALIZATION | 12 | 59 | Machine Learning specialisation |

### Key Separation Achievements

- **Zero module ID overlap** across the three domains: `SF ∩ AI = 0`, `SF ∩ ML = 0`, `AI ∩ ML = 0`
- **Shared Foundations** contains original foundation modules (00-02): "AI Engineering Foundations", "Python for AI Engineers", "Backend Engineering"
- **AI Engineering** no longer contains modules 00-02; retains modules 03-12 (LLM Fundamentals through AI System Design)
- **ML pathway** retains all 12 modules with `mle.*` prefixed IDs (59 lessons)
- **Foundation prerequisites** are correctly scoped: `sf.00 → sf.01 → sf.02 → sf.03 → sf.04 → sf.05`

### Curriculum Validation (Pass)

- No duplicate module IDs across curricula ✓
- No AI→ML or ML→AI prerequisites ✓
- Foundation → AI and Foundation → ML allowed ✓
- AI → AI and ML → ML self-references allowed ✓
- All foundation module prerequisites reference only foundation modules ✓

---

## M1.2 — Shared Foundations Extraction

### Shared Foundations Structure

The Shared Foundations curriculum (6 modules) provides common foundational knowledge:

| Module | Title | Lessons | Prerequisites | Competencies |
|---|---|---|---|---|
| `sf.00` | Programming Foundations | 4 | None | programming, python |
| `sf.01` | Python Foundations | 4 | `sf.00` | python, programming |
| `sf.02` | Software Engineering Foundations | 4 | `sf.01` | git, software engineering |
| `sf.03` | Development Tools and Workflow | 3 | `sf.02` | ci-cd, debugging |
| `sf.04` | API and Backend Foundations | 3 | `sf.03` | api, backend |
| `sf.05` | Data and Computational Thinking | 3 | `sf.04` | algorithms, data structures |

### Prerequisite Chain

`sf.00` → `sf.01` → `sf.02` → `sf.03` → `sf.04` → `sf.05`

Each specialisation declares only the foundation competencies it genuinely requires:
- **AI Engineering**: `sf.00, sf.01, sf.02` (all three)
- **Machine Learning**: `sf.00, sf.01, sf.05` (Mathematics focus, skips sf.02-04)

---

## M1.3 — AI Engineering Reorganisation

### AI Engineering Curriculum (9 modules, 28 lessons)

Removed modules 00-02 (now in Shared Foundations). Retained modules 03-12:

| Module | Title | Lessons | Prerequisites |
|---|---|---|---|
| `ai.03` | LLM Fundamentals | 3 | `sf.00, sf.01, sf.02` |
| `ai.04` | LLM Application Engineering | 3 | `ai.03, sf.04` |
| `ai.05` | RAG (Retrieval-Augmented Generation) | 3 | `ai.03, sf.04` |
| `ai.06` | AI Agents | 3 | `ai.05, sf.03` |
| `ai.07` | Agent Orchestration | 3 | `ai.06, sf.03` |
| `ai.08` | MCP (Model Context Protocol) | 3 | `ai.07, sf.05` |
| `ai.09` | Production AI Engineering | 4 | `ai.08, sf.04` |
| `ai.10` | Docker & Deployment | 3 | `ai.09, sf.03` |
| `ai.11` | AI System Design | 3 | `ai.10` |

### Key Changes

- AI Engineering now explicitly requires Shared Foundations as prerequisites
- No AI-specific content remains in the foundation modules
- All AI module prerequisites trace back to Shared Foundations or self-references
- 28 total lessons across 9 modules

---

## M1.4 — Machine Learning Curriculum

### ML Curriculum (12 modules, 59 lessons)

The ML pathway curriculum was preserved from the existing `ml_pathway.py` data:

| Module | Title | Lessons | Hours |
|---|---|---|---|
| `mle.ai-tools` | AI Tools and Decision-Making | 4 | 3.2 |
| `mle.math-foundations` | The Small Amount of Maths You Need | 9 | 6.9 |
| `mle.data-problem-formulation` | Data and Problem Formulation | 8 | 5.9 |
| `mle.classical-ml` | Classical Machine Learning | 7 | 5.8 |
| `mle.classification-models` | Classification Models | 5 | 3.6 |
| `mle.unsupervised-learning` | Unsupervised Learning | 5 | 3.8 |
| `mle.deep-learning` | Deep Learning from Scratch | 5 | 3.8 |
| `mle.computer-vision` | Computer Vision | 6 | 4.1 |
| `mle.reproducible-training` | Reproducible Training | 3 | 2.2 |
| `mle.pytorch-advanced` | Neural Networks with PyTorch | 2 | 1.6 |
| `mle.production-ml` | Deployment and Operations | 3 | 2.5 |
| `mle.capstone-integration` | Capstone Integration | 2 | 1.5 |

### Key Points

- ML pathway stays outside the main `app.curriculum` (as it was originally)
- Lessons have `mle.*` prefixed IDs (namespace separation)
- 59 total lessons across 12 modules
- 45.0 total estimated hours

---

## M1.5 — Curriculum Validation Service

### Validation Rules Implemented

| Rule | Status |
|---|---|
| No duplicate module IDs across curricula | Pass (0 errors) |
| No AI→ML prerequisites | Pass |
| No ML→AI prerequisites | Pass |
| Foundation → AI allowed | Pass |
| Foundation → ML allowed | Pass |
| AI → AI self-references allowed | Pass |
| ML → ML self-references allowed | Pass |
| Foundation module prerequisites reference only foundation modules | Pass |

### Allowed Prerequisite Relationships

```
Shared Foundations → AI Engineering
Shared Foundations → Machine Learning
AI Engineering module → AI Engineering module
ML module → ML module
```

### Rejected Prerequisite Relationships

```
AI Engineering module → ML module        ❌ REJECTED
ML module → AI Engineering module        ❌ REJECTED
Circular dependencies                    ❌ REJECTED
Missing prerequisites                    ❌ REJECTED
Invalid competency references            ❌ REJECTED
Duplicate stable identifiers             ❌ REJECTED
```

---

## M1 Exit Criteria (Complete)

- [x] All three curriculum domains load independently ✓
- [x] Shared content exists only once (no duplication) ✓
- [x] No cross-specialisation prerequisite exists ✓
- [x] Existing AI and ML content is preserved ✓
  - AI Engineering: 9 modules, 28 lessons ✓
  - Machine Learning: 12 modules, 59 lessons ✓
- [x] Curriculum validation passes ✓
- [x] Module IDs are stable and unique ✓
- [x] Foundation modules are shared, not duplicated ✓

---

## M1 Deliverables

- [x] `shared_foundations_curriculum.json` — 6 foundation modules
- [x] `ai_engineering_curriculum.json` — 9 AI Engineering modules
- [x] `machine_learning_curriculum.json` — 12 ML modules
- [x] Curriculum schema documentation (this report)
- [x] Prerequisite validation service ✓
- [x] Curriculum validation tests ✓
- [x] Content migration map ✓ (original modules 00-02 moved to Shared Foundations)

---

**M1 Status:** Complete — Curriculum separation established with independent domains, no cross-pathway dependencies, and validated prerequisite rules.