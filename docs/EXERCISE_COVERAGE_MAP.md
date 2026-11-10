# Exercise Coverage Map

Generated from the bundled curriculum and `app/data/practice_exercises.json`.
Each entry links an exercise to its lesson and lists that lesson’s authored
learning outcomes as context. Curriculum owners should verify the exact
exercise-to-outcome alignment during review.

| Module | Exercises |
|---|---:|
| 0. AI Engineering Foundations | 8 |
| 1. Python for AI Engineers | 17 |
| 2. Backend Engineering | 3 |
| 3. LLM Fundamentals | 6 |
| 4. LLM Application Engineering | 3 |
| 5. RAG (Retrieval-Augmented Generation) | 3 |
| 6. AI Agents | 4 |
| 7. Agent Orchestration | 3 |
| 8. MCP (Model Context Protocol) | 3 |
| 9. Production AI Engineering | 4 |
| 10. Docker & Deployment | 3 |
| 11. AI System Design | 2 |
| 12. Final Capstone: Build and Review an AI System | 3 |

## Lesson and outcome links

### Module 0 — AI Engineering Foundations

#### 0.01 — Welcome to the Course
- `first-python-greeting` (beginner; skills: foundations, python; prerequisites: none)
  Lesson outcomes:
  - Understand what an AI engineer does and how it's different from other roles (like data scientist or ML engineer)
  - Know the 13-module journey you'll take and see how each piece fits together into one big project
  - Set up your coding workspace (Git, Python, virtual environment) the right way from day one
  - Learn a simple, repeatable study routine that actually works for busy people
  - Create your first plan and know exactly what 'done' means for your learning

#### 0.03 — Anatomy of a Modern AI Application
- `foundations-system-map` (beginner; skills: foundations, python; prerequisites: none)
  Lesson outcomes:
  - Draw the six layers of an AI application and state the responsibility of each.
  - Follow a streamed request from client to persisted trace and name the artefacts produced.
  - Assign a timeout, validation rule, and fallback to every external dependency on the request path.

#### 0.06 — Your first Python program
- `python-first-script` (beginner; skills: foundations, python; prerequisites: none)
  Lesson outcomes:
  - Create a Python file and run it from a terminal with an explicit interpreter.
  - Store values in variables and format readable output with f-strings.
  - Use a traceback to find the line where a program failed.

#### 0.07 — Lists, dictionaries, and loops
- `python-inventory-value` (beginner; skills: foundations, python; prerequisites: none)
  Lesson outcomes:
  - Create lists and dictionaries and access values by position or key.
  - Use a loop to transform every item in a collection.
  - Use .get() and validation to avoid a KeyError on missing fields.

#### 0.08 — Functions, inputs, and return values
- `python-safe-divide` (beginner; skills: foundations, python; prerequisites: none)
  Lesson outcomes:
  - Define a function with parameters and a return value.
  - Validate inputs and raise a clear error when the contract is broken.
  - Call a function from a script and test it with several inputs.

#### 0.09 — Files, JSON, and the command line
- `python-json-summary` (beginner; skills: foundations, python; prerequisites: none)
  Lesson outcomes:
  - Read a text file with an explicit encoding.
  - Decode JSON and validate the shape you expect.
  - Pass a file path to a script with sys.argv and fail clearly when it is missing.

#### 0.10 — Git and GitHub from zero
- `git-conventional-message` (beginner; skills: foundations, git, python; prerequisites: none)
  Lesson outcomes:
  - Initialise a repository and make a first commit.
  - Write a commit message that explains why a change exists.
  - Keep secrets and generated files out of version control.

#### 0.11 — HTTP and APIs from zero
- `python-http-status` (beginner; skills: foundations, http, python; prerequisites: none)
  Lesson outcomes:
  - Send a GET request with an explicit timeout and read the status code.
  - Decode JSON only after checking that the response succeeded.
  - Distinguish client errors, server errors, and retryable failures.

### Module 1 — Python for AI Engineers

#### 1.01 — Python review: data, loops, and tracebacks
- `python-cheapest-by-provider` (intermediate; skills: data-structures, python; prerequisites: python-inventory-value)
  Lesson outcomes:
  - Understand Python's basic data types (strings, numbers, lists, dictionaries)
  - Work with lists and dictionaries to handle API responses
  - Write loops and conditions to process data
  - Read and understand Python error messages (tracebacks)
  - Know the difference between running a script vs running as a module

#### 1.02 — Python project structure
- `python-package-layout` (beginner; skills: packaging, python; prerequisites: none)
  Lesson outcomes:
  - Create a src layout with a package, an entry point, and a tests directory that imports the package without path hacks.
  - Draw the dependency direction between schemas, I/O, domain logic, and the command-line entry point.
  - Explain why python -m package avoids the import failures caused by running a file inside the package.

#### 1.03 — Functions
- `python-score-case` (intermediate; skills: python, testing; prerequisites: python-safe-divide)
  Lesson outcomes:
  - Write a function with an explicit contract: typed parameters, a single return shape, and documented failure behaviour.
  - Replace mutable default arguments and hidden global state with keyword-only parameters and injected dependencies.
  - Refactor a long procedure into three composable functions that can each be tested in isolation.

#### 1.04 — Type hints
- `python-safe-model-summary` (beginner; skills: python; prerequisites: none)
  Lesson outcomes:
  - Annotate functions and data shapes with builtin generics, unions, TypedDict, and Literal without resorting to Any.
  - Run mypy in strict mode on a package and triage errors by boundary, narrowing, and missing annotations.
  - Decide where runtime validation is still required despite a clean static check.

#### 1.05 — Classes & OOP
- `python-model-client` (beginner; skills: python; prerequisites: none)
  Lesson outcomes:
  - Decide whether a problem needs a class or a set of functions, using state, invariants, and call-site clarity as the test.
  - Write a client class with a constructor, private helpers, a factory, and a useful __repr__.
  - Replace inheritance with composition so transport, retries, and parsing can be tested and swapped independently.

#### 1.06 — Dataclasses
- `python-independent-dataclass-state` (beginner; skills: python; prerequisites: none)
  Lesson outcomes:
  - Define record types with the dataclass decorator, including defaults, field(default_factory=...), and computed properties.
  - Choose between mutable and frozen dataclasses based on whether identity or value semantics fit the data.
  - Explain why a dataclass is not a validation layer and where a schema model must take over.

#### 1.07 — Pydantic
- `python-validate-offer` (beginner; skills: python; prerequisites: none)
  Lesson outcomes:
  - Define a Pydantic model with field constraints, strict types, and cross-field validation for an external payload.
  - Validate JSON into typed objects with model_validate_json and reject unknown fields before they reach your code.
  - Read ValidationError locations to quarantine bad records while keeping the valid ones.

#### 1.08 — Error handling
- `python-bounded-retry` (intermediate; skills: http, python, reliability; prerequisites: python-http-status, python-model-client)
  Lesson outcomes:
  - Distinguish transient failures from permanent ones and choose retry, fallback, or fail-fast for each.
  - Build an exception hierarchy and re-raise with context so tracebacks preserve the original cause.
  - Route exhausted work to a dead-letter path and alert on skip rates instead of swallowing errors.

#### 1.09 — JSON
- `python-json-safe-roundtrip` (beginner; skills: python; prerequisites: none)
  Lesson outcomes:
  - Map Python values to JSON types and name the four values that need an explicit encoder.
  - Encode reports that reject NaN and read numbers back without losing decimal precision.
  - Choose between json.load, JSONL, and streaming for small, append-only, and large payloads.

#### 1.10 — HTTP requests
- `python-http-client-contract` (intermediate; skills: http, python, testing; prerequisites: python-bounded-retry)
  Lesson outcomes:
  - Build a request with the correct method, headers, JSON body, and status handling for an AI API.
  - Set connect and read timeouts, then retry only 429, 5xx, and timeouts within a total deadline.
  - Reuse a connection pool and validate the decoded response before it enters application code.

#### 1.11 — Environment variables
- `python-typed-settings` (beginner; skills: configuration, python; prerequisites: none)
  Lesson outcomes:
  - Move endpoints, credentials, and feature flags out of code and into environment variables with clear precedence.
  - Load settings into a typed object that fails fast with every invalid field named.
  - Store secrets so they never appear in Git, images, logs, or tracebacks.

#### 1.12 — Virtual environments
- `python-venv-audit` (beginner; skills: dependencies, python; prerequisites: none)
  Lesson outcomes:
  - Create a project virtual environment with a pinned Python version and use it without relying on activation.
  - Rebuild the environment from a lockfile in CI and containers, and prove the result matches.
  - Diagnose import shadowing and version drift using sys.prefix, pip check, and explicit interpreter paths.

#### 1.13 — Dependencies
- `python-dependency-audit` (beginner; skills: dependencies, python, security; prerequisites: none)
  Lesson outcomes:
  - Separate direct, transitive, and development dependencies, and explain why only direct ones belong in pyproject.toml.
  - Generate and verify a lockfile so installs resolve identically on a laptop, in CI, and in a container.
  - Audit a dependency set for version conflicts, abandoned packages, and supply-chain risk before merging.

#### 1.14 — Async Python
- `python-bounded-async-map` (intermediate; skills: async, python; prerequisites: none)
  Lesson outcomes:
  - Distinguish concurrency from parallelism and decide when an AI workload needs asyncio rather than threads or processes.
  - Explain how the event loop schedules coroutines and why one blocking call stalls every pending request.
  - Choose between asyncio.gather, TaskGroup, and a bounded semaphore for fan-out model calls.

#### 1.15 — async / await
- `python-taskgroup-deadline` (advanced; skills: async, python, reliability; prerequisites: python-bounded-async-map)
  Lesson outcomes:
  - Write async functions, await coroutines, and explain why calling one without awaiting returns a coroutine object.
  - Propagate exceptions and cancellation correctly across tasks, timeouts, and TaskGroup boundaries.
  - Use async context managers and async iterators to manage clients, sessions, and streamed responses.

#### 1.16 — Testing with pytest
- `python-mocked-http-contract` (intermediate; skills: http, python, testing; prerequisites: python-http-client-contract)
  Lesson outcomes:
  - Structure unit, integration, and contract tests so a failing build identifies the broken boundary.
  - Use fixtures, parametrisation, and mocking to test HTTP, timeouts, and malformed model output without network calls.
  - Make tests deterministic and fast enough to run as a required gate on every pull request.

#### 1.17 — Git & GitHub essentials
- `python-staged-secret-scan` (advanced; skills: python, security, testing; prerequisites: none)
  Lesson outcomes:
  - Create focused commits and branches that make a change easy to review, revert, and trace to an issue.
  - Resolve divergence with rebase or merge deliberately, and recover lost work with reflog and bisect.
  - Configure GitHub protection, review, and CI rules that keep main deployable and secrets out of history.

### Module 2 — Backend Engineering

#### 2.02 — HTTP
- `backend-normalize-http-headers` (beginner; skills: apis, backend, python; prerequisites: none)
  Lesson outcomes:
  - Break an HTTP/1.1 exchange into request line, headers, body, and status line, and explain what each part controls.
  - Choose status codes and methods that tell clients whether to retry, cache, or surface an error.
  - Diagnose a production issue using status codes, headers, and connection reuse evidence from logs and curl.

#### 2.13 — SQL
- `backend-customer-revenue` (beginner; skills: apis, backend, data-quality, databases, python; prerequisites: none)
  Lesson outcomes:
  - Replace per-row application loops with joins, aggregates, and window functions that return one result set.
  - Predict how inner and outer joins treat NULLs and use COUNT(*) and COALESCE correctly.
  - Write concurrent-safe updates with transactions, ON CONFLICT, and RETURNING, using bound parameters.

#### 2.19 — Background Jobs
- `backend-idempotent-job` (intermediate; skills: apis, backend, databases, python, reliability; prerequisites: none)
  Lesson outcomes:
  - Decide which work belongs in the request and which becomes a background job.
  - Design an idempotent job with persisted status, a retry policy, and progress records.
  - Detect stuck, duplicated, and poisoned jobs before users report them.

### Module 3 — LLM Fundamentals

#### 3.06 — Multimodal Model Inputs
- `multimodal-media-validation` (beginner; skills: ai-engineering, llm, python; prerequisites: none)
  Lesson outcomes:
  - Represent text, image, audio, and video inputs with explicit modality metadata.
  - Design size, duration, format, and privacy checks before model calls.
  - Choose task-specific quality measures for image understanding, transcription, and multimodal extraction.

#### 3.14 — Model Selection
- `llm-model-budget` (beginner; skills: ai-engineering, llm, python; prerequisites: none)
  Lesson outcomes:
  - Turn product requirements into hard constraints for context, latency, cost, and data handling before comparing models.
  - Benchmark candidate models on a frozen task set with confidence intervals instead of single-run impressions.
  - Design a routing rule that sends easy traffic to a cheaper model and hard cases to a stronger one.

#### 3.15 — Choosing and Adapting Model Deployments
- `model-deployment-decision` (beginner; skills: ai-engineering, llm, python; prerequisites: none)
  Lesson outcomes:
  - Compare hosted and self-hosted inference across privacy, latency, reliability, cost, and team capacity.
  - Explain when prompting, retrieval, fine-tuning, or distillation is a reasonable next step.
  - Design a representative benchmark and a rollback plan for an adapted or self-hosted model.

#### 3.16 — Open-weight and self-hosted models
- `open-weight-vram` (beginner; skills: ai-engineering, llm, python; prerequisites: none)
  Lesson outcomes:
  - Distinguish open-weight from open-source and read the licence before committing.
  - Estimate memory and throughput for a candidate model and quantization.
  - Compare hosted and self-hosted options with quality, latency, cost, and operational evidence.

#### 3.17 — Reasoning models and inference-time compute
- `reasoning-effort-router` (beginner; skills: ai-engineering, llm, python; prerequisites: none)
  Lesson outcomes:
  - Explain what inference-time compute buys and where it does not help.
  - Route easy, hard, and high-risk tasks to different effort levels.
  - Measure accuracy, latency, and cost before raising a reasoning budget.

#### 3.18 — Fine-tuning and adaptation decisions
- `adaptation-decision` (beginner; skills: ai-engineering, llm, python; prerequisites: none)
  Lesson outcomes:
  - Choose among prompting, retrieval, fine-tuning, and distillation for a given problem.
  - Prepare a clean training and evaluation split that does not leak answers.
  - Plan the serving, regression testing, and rollback for an adapted model.

### Module 4 — LLM Application Engineering

#### 4.03 — Structured Data Extraction
- `document-evidence-check` (beginner; skills: evaluation, llm, python; prerequisites: none)
- `llm-structured-evidence` (beginner; skills: evaluation, llm, python; prerequisites: none)
  Lesson outcomes:
  - Design an extraction schema that distinguishes a missing value from a confident zero or empty string.
  - Attach provenance to every extracted field and reject values that cannot be located in the source text.
  - Measure extraction with field-level precision and recall, then set the abstain threshold from that data.

#### 4.13 — Error Handling
- `llm-failure-policy` (beginner; skills: evaluation, llm, python; prerequisites: none)
  Lesson outcomes:
  - Map provider and application failures into retriable, terminal, and policy categories.
  - Implement jittered retries, timeouts, and a circuit breaker that respect the request deadline.
  - Return a structured error envelope with a stable code, request id, and safe retry guidance.

### Module 5 — RAG (Retrieval-Augmented Generation)

#### 5.02 — What Is RAG?
- `rag-rank-chunks` (beginner; skills: python, rag, retrieval; prerequisites: none)
  Lesson outcomes:
  - Describe the retrieve-then-generate loop and the three artefacts it produces: context, answer, and citation.
  - Decide when RAG is the right fix rather than fine-tuning, a longer prompt, or a plain database query.
  - Set a relevance threshold that makes the system abstain instead of generating from an empty context.

#### 5.17 — RAG Evaluation
- `rag-reciprocal-rank` (intermediate; skills: evaluation, python, rag, retrieval; prerequisites: rag-rank-chunks)
- `rag-ranking-metrics` (advanced; skills: evaluation, python, rag, retrieval; prerequisites: rag-reciprocal-rank)
  Lesson outcomes:
  - Separate retrieval metrics from generation metrics so a bad answer can be attributed to one stage.
  - Build a labelled question set that includes unanswerable, multi-hop, and exact-identifier cases.
  - Calibrate an LLM judge against human labels and wire thresholds into a regression gate.

### Module 6 — AI Agents

#### 6.01 — What Is an AI Agent?
- `agent-enforce-tool-budget` (intermediate; skills: agents, python, reliability, tool-calling; prerequisites: none)
  Lesson outcomes:
  - Define an agent as a goal, a model policy, a tool set, and a bounded observe-act loop rather than a clever prompt.
  - Distinguish autonomy that earns its cost from autonomy that only adds latency, spend, and unpredictable failure.
  - Specify stopping conditions, permissions, and a human escalation path before writing the first tool.

#### 6.07 — Designing Agent Tools
- `agent-tool-policy` (beginner; skills: agents, python, security, tool-calling; prerequisites: none)
  Lesson outcomes:
  - Write tool names, descriptions, and argument schemas that let a model choose the right tool without guessing.
  - Split broad API surfaces into task-shaped tools that each complete one verifiable unit of work.
  - Define error contracts, side-effect rules, and output limits so a tool is safe to call unattended.

#### 6.16 — Agent Security
- `agent-tool-authorization` (advanced; skills: agents, python, security, tool-calling; prerequisites: agent-tool-policy)
  Lesson outcomes:
  - Model the agent threat surface: prompt injection, excessive agency, data exfiltration, and confused-deputy tool use.
  - Apply least privilege to tool scopes, arguments, and egress, with approval for irreversible actions.
  - Contain a compromised run with sandboxing, allowlists, sanitised content, and a complete audit trail.

#### 6.18 — Computer-use and browser agents
- `computer-use-action-guard` (beginner; skills: agents, python, tool-calling; prerequisites: none)
  Lesson outcomes:
  - Design a small action schema that can be logged, replayed, and validated.
  - Run the agent in a sandbox with least-privilege credentials and no unnecessary secrets.
  - Require human approval for irreversible actions and provide a recovery path.

### Module 7 — Agent Orchestration

#### 7.09 — State Management
- `orchestration-state-machine` (advanced; skills: agents, orchestration, python; prerequisites: none)
  Lesson outcomes:
  - Define graph state as a TypedDict with annotated reducers and separate input, internal, and output fields.
  - Predict merge behaviour for parallel updates and replace a silent overwrite with a reducer.
  - Keep persisted state small and serialisable by moving credentials and large blobs out of it.

#### 7.17 — Production Agent Graph
- `orchestration-idempotency` (intermediate; skills: agents, orchestration, python; prerequisites: orchestration-state-machine)
  Lesson outcomes:
  - Draw the production graph from ingress to response, naming the state, side effects, and failure branch of each node.
  - Specify durability, budget, and timeout limits per node so a run cannot outlive its request or its cost ceiling.
  - Version the graph and its prompts together, then gate deploys on replaying a fixed set of recorded runs.

#### 7.18 — Agent-to-agent (A2A) collaboration
- `a2a-capability-router` (beginner; skills: agents, orchestration, python; prerequisites: none)
  Lesson outcomes:
  - Describe an agent card with capabilities, limits, and authentication requirements.
  - Design a handoff envelope that carries evidence, open questions, and a remaining budget.
  - Decide when a single agent or workflow is a better choice than A2A.

### Module 8 — MCP (Model Context Protocol)

#### 8.01 — What Is MCP?
- `mcp-validate-tool-call` (beginner; skills: mcp, python, security, tool-calling; prerequisites: none)
  Lesson outcomes:
  - Explain how an MCP host, client, and server divide discovery, consent, and execution without custom glue code.
  - Identify tools, resources, and prompts, and distinguish current stateless discovery from the legacy initialize handshake.
  - Decide when MCP is preferable to a direct API call, library, or fixed workflow.

#### 8.03 — MCP Architecture and Protocol Eras
- `mcp-protocol-era-selection` (beginner; skills: mcp, python, tool-calling; prerequisites: none)
  Lesson outcomes:
  - Distinguish handshake-era and 2026 stateless MCP requests.
  - Select stdio or Streamable HTTP independently from protocol lifecycle.
  - Build a compatibility test matrix for client, server, SDK, and protocol revisions.

#### 8.11 — MCP Security
- `mcp-permission-gate` (advanced; skills: mcp, python, security, tool-calling; prerequisites: mcp-validate-tool-call)
  Lesson outcomes:
  - Identify prompt injection through tool descriptions, resource text, and tool results in an MCP session.
  - Prevent confused-deputy and token-passthrough failures with per-server identity and scoped credentials.
  - Apply approval, sandboxing, egress control, and audit logging to high-risk MCP capabilities.

### Module 9 — Production AI Engineering

#### 9.01 — Prototype → Production
- `production-capped-retry-delays` (beginner; skills: python, reliability, security; prerequisites: none)
  Lesson outcomes:
  - Separate prototype questions about model capability from production questions about reliability, cost, and safety.
  - Convert a notebook demo into a service with contracts, timeouts, validation, telemetry, and a rollout plan.
  - Write a production-readiness review that names each gap, its failure mode, its owner, and the check that closes it.

#### 9.10 — AI Data Governance and Retention
- `ai-deletion-plan` (beginner; skills: python, reliability, security; prerequisites: none)
  Lesson outcomes:
  - Create a data inventory covering source, purpose, sensitivity, location, and owner.
  - Design retention and deletion behavior across application storage, logs, caches, evaluation data, and retrieval indexes.
  - Document provider data handling and escalation paths for a privacy or data-integrity incident.

#### 9.13 — AI Security and Risk Mapping
- `ai-risk-control-map` (beginner; skills: python, reliability, security; prerequisites: none)
  Lesson outcomes:
  - Map an AI feature’s attack surface and trust boundaries.
  - Use the current OWASP LLM risk categories as a coverage checklist, not as a substitute for threat modeling.
  - Assign each risk an owner, likelihood, impact, control, test, and response path.

#### 9.17 — LLM Evaluation
- `production-eval-summary` (advanced; skills: evaluation, python, reliability, security; prerequisites: none)
  Lesson outcomes:
  - Build a stratified evaluation set from real traffic, with labels, slices, and a documented sampling method.
  - Choose metrics that match the task, then report confidence intervals instead of a single pass rate.
  - Calibrate an LLM judge against human labels and state where it is safe to automate scoring.

### Module 10 — Docker & Deployment

#### 10.01 — Why Docker?
- `deployment-validate-container-config` (beginner; skills: deployment, docker, python, security; prerequisites: none)
  Lesson outcomes:
  - Explain why a lockfile alone cannot reproduce an AI service that depends on native libraries and model tooling.
  - Distinguish image, container, registry, and host, and state what each one owns during a deploy.
  - Decide whether a container is the right packaging boundary for a given workload and team.

#### 10.03 — Dockerfile
- `deployment-config-gate` (advanced; skills: deployment, docker, python, security; prerequisites: deployment-validate-container-config)
  Lesson outcomes:
  - Order Dockerfile instructions so dependency layers survive source changes and rebuilds stay under a minute.
  - Use a multi-stage build to keep compilers and build caches out of the runtime image.
  - Run the service as a non-root user with an exec-form entrypoint that receives SIGTERM.

#### 10.07 — Production Containers
- `container-release-readiness` (intermediate; skills: deployment, docker, python, security; prerequisites: deployment-validate-container-config)
  Lesson outcomes:
  - Convert a single-stage build into a multi-stage image that ships no compilers, caches, or test fixtures.
  - Harden the runtime with a non-root user, read-only filesystem, pinned base, and explicit signal handling.
  - Verify image size, vulnerability count, and shutdown behaviour before the image reaches a registry.

### Module 11 — AI System Design

#### 11.01 — AI System Design
- `system-design-route-by-budget` (beginner; skills: cost, python, reliability, system-design; prerequisites: none)
- `system-design-budget` (advanced; skills: cost, python, reliability, system-design, testing; prerequisites: none)
  Lesson outcomes:
  - Separate product constraints from model choices, and record each decision with an owner and its consequences.
  - Draw the request, data, and state flows, then mark every trust boundary and external dependency on one diagram.
  - Set latency, cost, and failure budgets per stage, and name the degraded behaviour when a dependency is unavailable.

### Module 12 — Final Capstone: Build and Review an AI System

#### 12.01 — Phase 1 — Requirements
- `capstone-requirement-checklist` (intermediate; skills: capstone, python, testing; prerequisites: none)
- `capstone-requirement-trace` (intermediate; skills: capstone, python, testing; prerequisites: capstone-requirement-checklist)
  Lesson outcomes:
  - Write requirements as actor, trigger, observable outcome, and threshold, so each one can pass or fail in a test.
  - Set quality, latency, cost, and safety budgets from the decision the platform supports, not from vendor claims.
  - Build a traceability matrix that links every requirement to an evaluation case, a dashboard metric, and an owner.

#### 12.09 — Phase 9 — Choose the Right Orchestration Shape
- `orchestration-evidence-choice` (beginner; skills: capstone, python, testing; prerequisites: none)
  Lesson outcomes:
  - Compare a deterministic workflow, a single bounded agent, and a multi-agent design against stated requirements.
  - Use trace and evaluation evidence to justify any orchestration split.
  - Measure routing, handoff, quality, latency, cost, and failure propagation when multiple agents are warranted.
