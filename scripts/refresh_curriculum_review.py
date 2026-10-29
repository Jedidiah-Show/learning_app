"""Apply the AI engineering curriculum review while preserving lesson IDs."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'app' / 'data'
CURRICULUM_PATH = DATA / 'dynamoai_curriculum.json'


def lesson_spec(title, subtitle, why, outcomes, concepts, example, steps,
                mistakes, production, checklist, questions, tasks, capstone,
                code=None):
    return {
        'title': title,
        'subtitle': subtitle,
        'why_it_matters': [why],
        'outcomes': outcomes,
        'core_concepts': [{'title': name, 'content': body} for name, body in concepts],
        'mental_model': subtitle,
        'worked_example': [example],
        'steps': steps,
        'code': code or {},
        'common_mistakes': mistakes,
        'production_notes': production,
        'checklist': checklist,
        'questions': questions,
        'tasks': tasks,
        'capstone': capstone,
    }


SPECS = {
    '3.05': lesson_spec(
        'Generation Controls and Nondeterminism',
        'Treat sampling settings as experimental controls; measure output behavior instead of assuming one setting is universally best.',
        'Temperature and sampling shape a distribution of possible outputs, but they do not make a model reliable or deterministic. Knowing which controls a provider actually supports helps you design fair evaluations and avoid false confidence from one lucky response.',
        ['Explain how temperature and nucleus sampling affect token selection at a high level.', 'Compare repeated outputs using a fixed dataset and task-specific metrics.', 'Record provider-supported generation settings and distinguish reproducibility from determinism.'],
        [('Sampling is a distribution', 'A language model assigns probabilities to next tokens. Decoding selects from that distribution; temperature reshapes relative probabilities and nucleus sampling limits the candidate set. These controls affect variation, not factuality or instruction-following guarantees.'), ('Settings are provider-specific', 'APIs differ in accepted parameters, defaults, and support. Some model families ignore or reject familiar settings. Store the settings actually sent and returned with each evaluation result; do not rely on an undocumented default.'), ('Repeatability has limits', 'A fixed seed or low temperature may reduce variation where supported, but hosted systems can change infrastructure and model snapshots. Evaluate multiple runs when variance matters, and pin model versions where possible.')],
        'A support team tests two settings on the same 80 questions, runs each case three times, and compares policy compliance, correct resolution, and answer variance. The team chooses a setting from measured results rather than assuming the lowest temperature is automatically safest.',
        ['Choose a task and define what counts as a correct, safe, and useful response.', 'Freeze a small representative dataset and record the model identifier and API parameters.', 'Run repeated trials for each supported setting; keep raw outputs and request metadata.', 'Compare task metrics and variance by important user or language slice.', 'Document the chosen setting as a hypothesis with a reevaluation trigger.'],
        ['Treating temperature zero as a guarantee of deterministic output.', 'Comparing settings on different prompts or different examples.', 'Assuming every provider accepts the same decoding parameters.', 'Using fluent style as a substitute for task correctness.'],
        ['Record the exact model snapshot, decoding fields, seed behavior, and SDK/API version used by an evaluation.', 'Keep response variance visible for high-impact tasks and set retry behavior independently from sampling.', 'Re-run the comparison when the provider changes model behavior or removes a parameter.'],
        ['I can describe sampling without claiming it verifies truth.', 'I have a fixed evaluation set and repeat runs.', 'I record provider, model, parameters, and result metadata.', 'My choice is based on task metrics and variance.'],
        ['Why can temperature zero still produce different results?', 'What does nucleus sampling limit?', 'Why should the model and API version accompany each result?', 'How would you tell a style change from a quality change?', 'When is repeated-run variance important?'],
        ['Run a repeated-output comparison for two settings on at least 30 cases and report quality and variance separately.', 'Write a provider-neutral generation configuration that rejects unsupported settings instead of silently dropping them.'],
        'Provides the capstone evaluation with an explicit generation configuration and reproducible run metadata.',
    ),
    '3.06': lesson_spec(
        'Multimodal Model Inputs',
        'Build model workflows that handle images, audio, and video as typed, bounded inputs with modality-specific evaluation.',
        'Real AI products often receive screenshots, scanned forms, voice notes, or short clips. Treating all of these as plain text hides important costs, privacy risks, and failure modes such as unreadable text, clipped audio, and missing visual context.',
        ['Represent text, image, audio, and video inputs with explicit modality metadata.', 'Design size, duration, format, and privacy checks before model calls.', 'Choose task-specific quality measures for image understanding, transcription, and multimodal extraction.'],
        [('A request has modality and provenance', 'Model input may contain text, image bytes or URLs, audio, video frames, or combinations. Record where each asset came from, its media type, dimensions or duration, and any preprocessing. Keep those assets under the same access and retention policy as the text prompt.'), ('Preprocessing changes evidence', 'Image resizing, page rendering, cropping, audio segmentation, and video frame selection can remove information. Record these transformations and test representative edge cases such as rotated scans, low contrast, accents, background noise, and rapid scene changes.'), ('Evaluate each modality', 'A text answer can sound plausible while missing visual details or mishearing a name. Measure the actual task: field accuracy and source location for documents, word error or named-entity accuracy for transcription, and event or timestamp accuracy for video. Include abstention when the input is unclear.')],
        'An expense assistant receives a phone photo of a receipt and an optional spoken note. It checks media type and size, stores each asset with the user’s access scope, extracts fields with evidence locations, and asks for review when the image is blurred or the spoken amount conflicts with the receipt.',
        ['Define accepted modalities and reject unsupported formats at the boundary.', 'Set limits for bytes, dimensions, duration, and number of video frames.', 'Record preprocessing and retain source references needed for audit or user correction.', 'Create labeled examples for clear, ambiguous, and out-of-distribution inputs.', 'Compare quality, latency, and cost across representative modality slices.'],
        ['Assuming a model can inspect a file merely because its URL is in a text prompt.', 'Sending private media to a provider without checking data handling and retention.', 'Evaluating only easy, clean images or studio-quality audio.', 'Discarding the source asset before a user can correct an extracted value.'],
        ['Treat uploaded files as untrusted: scan, bound, decode safely, and store outside public paths.', 'Use least-privilege access and short retention for raw media; log references and hashes rather than sensitive payloads.', 'Make provider capabilities explicit in adapters because modality support and input limits vary.'],
        ['Inputs have modality, provenance, and access scope.', 'Media limits run before model spend.', 'Preprocessing is documented and reproducible.', 'Evaluation includes modality-specific errors and ambiguous inputs.', 'Users can correct consequential extracted data.'],
        ['What information should be logged for a video frame selection?', 'Why is transcription quality not the same as final answer quality?', 'What risks arise from public image URLs?', 'How would you measure a blurry-input fallback?', 'When should the system ask the user to clarify?'],
        ['Implement a pure validation function for media metadata and test invalid type, oversize image, and excessive audio duration.', 'Build a 20-example multimodal evaluation plan with at least five ambiguous or degraded inputs.', 'Compare one image extraction workflow with OCR-first and direct-vision approaches using the same labeled fields.'],
        'Adds image/document and audio inputs to the capstone’s model adapter and evaluation plan; video remains an optional extension.',
        {'title': 'Validate modality metadata before a provider call.', 'language': 'python', 'code': 'ALLOWED = {"text", "image", "audio", "video"}\n\ndef validate_media(item, max_bytes=10_000_000, max_seconds=120):\n    if item.get("modality") not in ALLOWED:\n        return "unsupported_modality"\n    if item.get("bytes", 0) < 0 or item.get("bytes", 0) > max_bytes:\n        return "invalid_size"\n    duration = item.get("duration_seconds")\n    if item["modality"] in {"audio", "video"} and (duration is None or duration < 0 or duration > max_seconds):\n        return "invalid_duration"\n    return None', 'what_to_notice': ['This example checks metadata only; production systems must also validate decoded content and authorization.', 'Limits are product policy and should be selected from provider limits, user needs, and cost targets.']},
    ),
    '3.15': lesson_spec(
        'Choosing and Adapting Model Deployments',
        'Compare hosted APIs, self-hosted open weights, fine-tuning, and distillation using workload evidence and operating costs.',
        'The hosted-versus-open label is too crude for an architecture decision. Teams must choose who operates inference, where data flows, how versions change, and whether adaptation beats retrieval or better prompting.',
        ['Compare hosted and self-hosted inference across privacy, latency, reliability, cost, and team capacity.', 'Explain when prompting, retrieval, fine-tuning, or distillation is a reasonable next step.', 'Design a representative benchmark and a rollback plan for an adapted or self-hosted model.'],
        [('Deployment is an operating choice', 'Hosted APIs reduce infrastructure work but create provider dependency and data-flow constraints. Self-hosted weights add control but require serving, scaling, security updates, GPU capacity planning, and model artifact governance. Compare total cost at realistic utilization, not a single token price.'), ('Adaptation has an evidence threshold', 'Start with a clear task specification, examples, retrieval, and evaluation. Fine-tuning can help when behavior or format is consistently wrong and representative training data exists; it does not reliably add fresh facts or remove the need for retrieval. Distillation can reduce serving cost after a stronger system establishes a validated target.'), ('Version the whole system', 'Track weights, tokenizer, serving runtime, quantization, adapters, prompt, and evaluation dataset together. Compare quality, latency, memory, and cost against a fixed baseline, then use staged rollout and a tested rollback.')],
        'A team has a private support corpus and frequent policy updates. It first tests retrieval with a hosted model under approved data terms. It considers self-hosting only after a measured concurrency and privacy requirement justifies the operations cost, and does not fine-tune facts that change weekly.',
        ['Write the workload envelope: data sensitivity, traffic, latency, quality, availability, and cost.', 'Benchmark at least one hosted and one self-hosted candidate if both are plausible.', 'Compare prompt-only, retrieval, and fine-tuning options against the same labeled task set.', 'Include GPU or provider spend, engineering time, and operational support in total cost.', 'Record artifact versions, staged rollout checks, and rollback triggers.'],
        ['Treating open weights as automatically private or free.', 'Fine-tuning before a labeled baseline shows a repeatable gap.', 'Comparing model quality on different examples or different output constraints.', 'Ignoring serving utilization, upgrades, security patches, and fallback behavior.'],
        ['Check licenses and usage terms for model weights, datasets, and adapters.', 'Pin and scan model artifacts; restrict who can publish or replace production weights.', 'Re-evaluate model quality and safety after quantization, runtime, tokenizer, or hardware changes.'],
        ['I can state who operates the model and where data flows.', 'My choice uses a representative benchmark and total cost.', 'I can explain why retrieval or prompting is or is not enough.', 'The model artifact and serving stack are versioned.', 'Rollback has a measurable trigger.'],
        ['When does fine-tuning fail to solve a knowledge freshness problem?', 'Which operational costs are easy to omit from self-hosted estimates?', 'Why can quantization change task quality?', 'What evidence would justify moving from hosted to self-hosted inference?', 'Which artifacts belong in a reproducible model release?'],
        ['Write an ADR comparing hosted and self-hosted deployment for one workload.', 'Create a decision table for prompt, retrieval, fine-tuning, and distillation with evidence thresholds.', 'Define a staged rollout and rollback rule for a model artifact change.'],
        'Informs the capstone model selection ADR and gives the team an evidence-based reason to self-host or adapt a model.',
    ),
    '7.02': lesson_spec(
        'Framework Case Study: LangChain',
        'Learn orchestration patterns first, then use LangChain as one replaceable, versioned implementation.',
        'Framework APIs change faster than core engineering principles. A learner should understand the underlying adapter and workflow before adopting a package that may add dependencies or migration work.',
        ['Map framework components to ordinary application concepts.', 'Pin the package version and identify framework-specific coupling.', 'Keep prompts, schemas, tools, and evaluation portable across framework changes.'],
        [('Pattern before package', 'A chain is a sequence of transformations; a runnable composes inputs, steps, and outputs. These ideas can be implemented directly in Python. The framework provides conventions and integrations, not a guarantee of better quality.'), ('Adapters define the boundary', 'Wrap model and retrieval integrations behind application-owned interfaces. Convert framework objects at the edge so domain logic and tests do not depend on framework data types.'), ('Review the maintenance cost', 'Check release cadence, migration guidance, observability support, and dependency footprint. Keep a representative evaluation so upgrades can be measured.')],
        'A team prototypes a retrieval flow with a framework, then places its model and retriever behind local interfaces. It compares that path with a short direct implementation before committing to the dependency.',
        ['Identify the orchestration pattern being demonstrated.', 'Pin the framework and record its official documentation version.', 'Implement a small path behind application-owned input and output types.', 'Test domain rules without importing the framework.', 'Write an ADR describing benefit, coupling, and upgrade plan.'],
        ['Treating a library abstraction as the product architecture.', 'Passing framework objects through every business layer.', 'Following an old tutorial without checking the pinned version.', 'Assuming the framework provides evaluation, authorization, or operations controls.'],
        ['Pin versions and review dependency changes.', 'Keep prompts, schemas, provider calls, and evaluation at the application boundary.', 'Test upgrades against recorded cases before rollout.'],
        ['I can explain the pattern without naming the package.', 'Framework types stay at an adapter boundary.', 'Dependencies are pinned.', 'A repeatable evaluation checks the framework path.'],
        ['What problem does the package solve here?', 'Which abstractions could be replaced with ordinary functions?', 'How would an upgrade change behavior?', 'Which tests should remain framework-independent?'],
        ['Build one small framework-backed workflow and compare it with direct control flow.', 'Write an upgrade checklist for state, streaming, tracing, and provider integrations.'],
        'The capstone uses a framework only when it reduces measured implementation work.',
    ),
    '7.03': lesson_spec(
        'Framework Case Study: LangGraph',
        'Model orchestration as explicit state transitions, then evaluate LangGraph as one versioned graph runner.',
        'Graphs help when execution branches, loops, pauses, or resumes. The graph is a design model; a framework is an implementation whose persistence and streaming guarantees must be verified.',
        ['Represent nodes, state, transitions, and stop conditions explicitly.', 'Distinguish deterministic routing from model-selected actions.', 'Test persistence, retries, and replay independently of framework convenience APIs.'],
        [('A graph is a contract', 'Each node has typed inputs and outputs; each edge describes a transition. State changes should be explicit so reviewers can see what information and authority move between steps.'), ('Execution is versioned', 'A graph framework can provide checkpointing and streaming integrations. Pin the version and determine which guarantees belong to the library, storage backend, or application.'), ('Keep behavior testable', 'Test node functions as ordinary code, then test transitions and checkpoint resume. Record framework and checkpoint schema versions so a deployment can recover old runs.')],
        'An approval workflow retrieves a document, drafts an action, pauses for a person, and resumes. The graph makes the pause and state explicit; authorization and the approval decision remain application controls.',
        ['Draw nodes and typed state before selecting a library.', 'Separate deterministic conditions from model decisions.', 'Pin the framework and define a checkpoint schema.', 'Test nodes, branches, pause/resume, and failures.', 'Compare a framework-free implementation when the workflow is small.'],
        ['Assuming graph persistence makes side effects exactly once.', 'Putting permissions in state without validating them when executing.', 'Retrying a non-idempotent node without an idempotency design.', 'Coupling every application contract to framework objects.'],
        ['Persist explicit schema versions and define migration or expiry for old runs.', 'Recheck authorization after resume and use idempotency keys for writes.', 'Evaluate upgrades against representative traces.'],
        ['The graph has explicit state and stop conditions.', 'Authorization is checked at action boundaries.', 'External writes have idempotency behavior.', 'Checkpoint resume is tested.'],
        ['Which transitions are deterministic?', 'What happens if a process restarts during approval?', 'Where does idempotency belong?', 'Which parts of the graph are application contracts?'],
        ['Implement a small approval graph and test restart/resume with a fake tool.', 'Compare a graph framework with direct Python control flow in an ADR.'],
        'A graph framework is optional for capstone workflows with real branching or durable pause/resume needs.',
    ),
    '9.10': lesson_spec(
        'AI Data Governance and Retention',
        'Track data provenance, purpose, access, retention, and deletion through prompts, retrieval, logs, and model-provider boundaries.',
        'AI systems copy data across more places than ordinary request handlers: prompts, traces, vector indexes, caches, evaluation sets, and provider services. A retention or access policy is incomplete until those copies and their deletion paths are known.',
        ['Create a data inventory covering source, purpose, sensitivity, location, and owner.', 'Design retention and deletion behavior across application storage, logs, caches, evaluation data, and retrieval indexes.', 'Document provider data handling and escalation paths for a privacy or data-integrity incident.'],
        [('Data lineage follows the request', 'A user message can be copied into a prompt, trace, cache, analytics table, evaluation set, and vector index. Record these destinations and the purpose for each. Avoid collecting raw prompt or response bodies by default when metadata is sufficient.'), ('Deletion must reach derived stores', 'Deleting a source row does not remove its chunks, embeddings, cached answers, backups, or evaluation fixtures. Define deletion propagation, tombstones, reindex behavior, backup expiry, and a verification signal. Keep access filtering in retrieval even while deletion work is pending.'), ('Governance is an operating process', 'Assign owners for data classes and retention rules. Review provider terms, residency, and subprocessors before sending sensitive data. Keep a route for user requests, legal holds, incident response, and documented exceptions.')],
        'A customer requests deletion of a document. The service marks the source unavailable immediately, removes its retrieval ACL, queues deletion for chunks and embeddings, invalidates answer caches, and verifies completion across each store before closing the request.',
        ['Draw the data-flow path from source to model and every derived store.', 'Label each field with purpose, sensitivity, owner, and retention duration.', 'Specify deletion, backup expiry, legal-hold, and evaluation-data handling.', 'Remove raw payloads from default logs; use redaction or references when debugging needs them.', 'Test a deletion request end to end and record proof for every destination.'],
        ['Treating vector embeddings as anonymous or harmless by default.', 'Deleting a source file but leaving indexed chunks searchable.', 'Copying production prompts into a permanent benchmark without minimization.', 'Assuming a provider’s general privacy statement answers every product configuration question.'],
        ['Use tenant and object authorization on source fetch, retrieval, cache lookup, and result display.', 'Keep a deletion ledger for asynchronous cleanup and alert on overdue destinations.', 'Review data handling whenever a provider, region, model feature, or observability vendor changes.'],
        ['Every data copy has an owner, purpose, and retention rule.', 'Deletion includes caches and retrieval indexes.', 'Provider handling is reviewed for the selected service and configuration.', 'Raw prompt and response logging is minimized.', 'A deletion test proves completion across stores.'],
        ['Why can an embedding still be sensitive?', 'What should happen before asynchronous deletion finishes?', 'How can a benchmark dataset accidentally become a new data store?', 'Which metadata is useful for traces without retaining raw content?', 'How should legal holds interact with a deletion request?'],
        ['Create a data inventory for one RAG feature and mark each derived store.', 'Implement a pure deletion-plan function that returns required destinations for a document.', 'Write a short runbook for a provider data-handling incident.'],
        'Adds a data inventory and verified deletion workflow to the capstone’s RAG and observability design.',
    ),
    '9.13': lesson_spec(
        'AI Security and Risk Mapping',
        'Threat-model model, data, retrieval, tool, and supply-chain boundaries using current AI risk taxonomies and enforceable controls.',
        'Prompt injection is only one part of AI security. Production reviews also need to consider sensitive-data disclosure, vector-store weaknesses, supply-chain integrity, unbounded spend, unsafe outputs, and overreliance on model judgments.',
        ['Map an AI feature’s attack surface and trust boundaries.', 'Use the current OWASP LLM risk categories as a coverage checklist, not as a substitute for threat modeling.', 'Assign each risk an owner, likelihood, impact, control, test, and response path.'],
        [('Threats span the full system', 'Review user and retrieved content, model outputs, tool execution, authorization, embeddings, external packages, model artifacts, and operational limits. The OWASP 2025 categories include prompt injection, sensitive information disclosure, supply-chain vulnerabilities, data and model poisoning, improper output handling, excessive agency, system-prompt leakage, vector and embedding weaknesses, misinformation, and unbounded consumption.'), ('Controls need an enforcement point', 'A prompt instruction is not an access-control boundary. Enforce tenant permissions in data queries, validate output before downstream use, bound tokens and concurrency, scope tool credentials, and require approval for actions whose effects are hard to reverse.'), ('Risk management continues after launch', 'Keep a risk register linked to tests, owners, and incidents. NIST’s Generative AI Profile provides a lifecycle frame for governing, mapping, measuring, and managing risks. Revisit the assessment when data, model, tools, or deployment context changes.')],
        'A RAG assistant has private documents and a tool that can email summaries. The review tests cross-tenant retrieval, malicious instructions in a document, prompt leakage attempts, output rendering, tool recipient constraints, provider data handling, and request-cost exhaustion.',
        ['Draw the data flow and mark every boundary between user, application, model, tools, stores, and providers.', 'List assets and abuse cases, including misuse and operational failure.', 'Map each risk to a deterministic control where possible and a test that proves it.', 'Assign severity, owner, residual risk, monitoring signal, and response action.', 'Review the register after significant changes and after incidents.'],
        ['Treating the OWASP list as a complete threat model.', 'Using a classifier as the only protection against unauthorized access.', 'Logging sensitive attack payloads without retention controls.', 'Calling a risk mitigated because a prompt says not to do it.'],
        ['Include resource exhaustion, software/model artifact integrity, tenant isolation, and human review in release gates.', 'Run tests using adversarial content from sources the model can retrieve, not only direct user prompts.', 'Document residual risk and operational owners; risk does not disappear when the model provider changes.'],
        ['The diagram shows data, identity, and tool boundaries.', 'Every high-severity risk has an enforceable control and a test.', 'OWASP categories are mapped to this system’s actual assets.', 'Owners and incident actions are recorded.', 'The assessment has a review trigger.'],
        ['Which 2025 OWASP category applies to poisoned retrieval content?', 'Why is prompt text not authorization?', 'What evidence would show a tenant-isolation control works?', 'How should an unbounded-cost risk be detected?', 'When should a risk assessment be repeated?'],
        ['Threat-model one feature using the 2025 OWASP LLM categories and write five executable abuse cases.', 'Build a risk register with eight entries, owners, tests, residual risk, and review triggers.', 'Write an incident tabletop scenario for cross-tenant retrieval or tool misuse.'],
        'Supplies the capstone with a reviewable risk register, abuse tests, and owners for residual risks.',
    ),
    '12.09': lesson_spec(
        'Phase 9 — Choose the Right Orchestration Shape',
        'Use traces and evaluation evidence to choose a deterministic workflow, one agent, or multiple agents; multi-agent design is an optional branch.',
        'Adding agents adds calls, latency, cost, and failure paths. A capstone should demonstrate sound architecture judgment, including the ability to reject a multi-agent design when one bounded agent or a deterministic workflow meets the requirements.',
        ['Compare a deterministic workflow, a single bounded agent, and a multi-agent design against stated requirements.', 'Use trace and evaluation evidence to justify any orchestration split.', 'Measure routing, handoff, quality, latency, cost, and failure propagation when multiple agents are warranted.'],
        [('Start with the simplest adequate control flow', 'Use deterministic code for known sequences, validation, permissions, and transactions. Use one agent when model-led tool choice adds value. Use multiple agents only when distinct context, permissions, ownership, or independently measurable work justify coordination.'), ('A split needs a measurable hypothesis', 'Name the failure a specialist is meant to reduce and define a baseline. Compare the split against the same task set and include handoff errors, duplicate work, extra model calls, latency, and spend. More workers do not imply more correctness.'), ('Preserve one accountable result', 'Whether the workflow has one model or several, the application owns authorization, budgets, state validation, and the final response contract. Each delegated step receives only the required data and capabilities.')],
        'The capstone’s document assistant has a fixed retrieve, rank, answer pipeline. Its team first evaluates a single agent for ambiguous queries. Only if traces show repeated tool-selection failures that a specialized retriever can measurably reduce does the team prototype a second agent.',
        ['Write the task requirements and baseline success, safety, latency, and cost metrics.', 'Implement the simplest plausible workflow and collect representative traces.', 'Identify a specific failure that added orchestration could address.', 'Prototype the alternative behind a feature flag using the same evaluation set.', 'Keep the split only if it improves the target without violating safety or budgets; record the decision either way.'],
        ['Adding agents because the capstone checklist expects them.', 'Comparing a tuned multi-agent system with an untuned single-agent baseline.', 'Scoring only the final answer and ignoring tool permissions or trajectory.', 'Sharing unrestricted state and credentials across specialists.'],
        ['Set hard per-run model, step, wall-clock, and tool-call budgets.', 'Persist only validated state and give each worker minimum necessary data and permissions.', 'Keep the no-split decision as valid architecture evidence when measurements do not justify extra agents.'],
        ['The baseline architecture is implemented and evaluated.', 'Any proposed split has a named failure hypothesis.', 'Results compare quality, safety, latency, and cost on the same cases.', 'The final design has explicit budgets and ownership.', 'The ADR records why a split was accepted or rejected.'],
        ['When is a deterministic workflow preferable to an agent?', 'What evidence would justify a specialist agent?', 'How can handoffs create a new security boundary?', 'What metrics can worsen while answer quality improves?', 'Why is rejecting multi-agent architecture a valid capstone result?'],
        ['Write an ADR comparing workflow, single-agent, and multi-agent options.', 'Evaluate at least 30 representative runs and report quality, trajectory, latency, and cost.', 'If multi-agent is not justified, document the evidence and improve the simplest design instead.'],
        'Replaces the mandatory supervisor-plus-three-specialists build with an evidence-based architecture decision and optional implementation.',
    ),
}


def render_pages(lesson_id, module_title, spec):
    concepts = '\n\n'.join(
        f"{item['title']}\n{item['content']}" for item in spec['core_concepts']
    )
    return [
        f"{spec['title']}\n{spec['subtitle']}\n{module_title} · Lesson {lesson_id} · study guide\n\nWHY THIS LESSON MATTERS\n{spec['why_it_matters'][0]}\n\nWHAT YOU WILL BE ABLE TO DO\n" + '\n'.join('• ' + x for x in spec['outcomes']) + '\n\nCORE CONCEPTS\n' + concepts,
        f"{spec['title']}\nBuild it\n\nWORKED EXAMPLE\n{spec['worked_example'][0]}\n\nSTEP BY STEP\n" + '\n'.join(f'{i}. {x}' for i, x in enumerate(spec['steps'], 1)) + ('\n\nCODE\n' + spec['code'].get('code', '') + '\n\nWHAT TO NOTICE\n' + '\n'.join('• ' + x for x in spec['code'].get('what_to_notice', [])) if spec['code'] else ''),
        f"{spec['title']}\nOperate it\n\nCOMMON MISTAKES\n" + '\n'.join(f'{i}. {x}' for i, x in enumerate(spec['common_mistakes'], 1)) + '\n\nPRODUCTION NOTES\n' + '\n'.join('◆ ' + x for x in spec['production_notes']) + '\n\nCHECKPOINT CHECKLIST\n' + '\n'.join('□ ' + x for x in spec['checklist']) + '\n\nSHORT QUESTIONS\n' + '\n'.join(f'{i}. {x}' for i, x in enumerate(spec['questions'], 1)) + '\n\nTASKS\n' + '\n'.join('□ ' + x for x in spec['tasks']) + '\n\nCAPSTONE CONNECTION\n' + spec['capstone'],
    ]


def apply_spec(lesson, spec, module_title):
    lesson.update(spec)
    lesson['pages'] = render_pages(lesson['id'], module_title, spec)
    lesson['meta'] = f"{module_title} · study guide · reviewed 2026"


def main():
    data = json.loads(CURRICULUM_PATH.read_text(encoding='utf-8'))
    modules = {m['id']: m for m in data['modules']}
    lessons = {lesson['id']: lesson for lesson in data['lessons']}
    for lesson_id, spec in SPECS.items():
        lesson = lessons[lesson_id]
        module = modules[lesson['module_id']]
        apply_spec(lesson, spec, module['title'])
        nested = next(item for item in module['lessons'] if item['id'] == lesson_id)
        apply_spec(nested, spec, module['title'])

    # Refresh the MCP architecture lessons to teach both wire eras and require
    # protocol-version checks in implementations.
    mcp_updates = {
        '8.03': {
            'title': 'MCP Architecture and Protocol Eras',
            'subtitle': 'Understand the handshake-era protocol and the stateless 2026 protocol, then select compatible SDK behavior deliberately.',
            'concepts': [('Two protocol eras', 'MCP revisions through 2025-11-25 use initialize and a negotiated session. Revision 2026-07-28 removes that exchange and session identifier: requests carry their version and metadata, and clients may use server/discover. Learn both because deployed hosts and servers will coexist.'), ('Transport and lifecycle are separate choices', 'stdio is a local process transport; Streamable HTTP supports remote deployments. Do not infer protocol lifecycle from transport alone. A client may need explicit negotiation or a compatibility fallback based on the peers it supports.'), ('Version the contract you ship', 'Record protocol revision, SDK version, transport, negotiated era, and enabled capabilities. Test old and new peers, authentication, cancellation, errors, and any state your application maintains outside the protocol.')],
            'outcomes': ['Distinguish handshake-era and 2026 stateless MCP requests.', 'Select stdio or Streamable HTTP independently from protocol lifecycle.', 'Build a compatibility test matrix for client, server, SDK, and protocol revisions.'],
        },
        '8.04': {
            'title': 'MCP Clients and Compatibility',
            'subtitle': 'Build clients that discover or initialize according to protocol support and still enforce host policy on every tool call.',
            'concepts': [('Connect with a declared compatibility policy', 'For handshake-era peers, initialize negotiates protocol and capabilities. For 2026 peers, use the supported stateless discovery and per-request metadata behavior. SDK defaults may not opt into the newest revision automatically; verify rather than assume.'), ('Policy stays in the host', 'Protocol compatibility does not grant authority. Filter advertised capabilities, validate arguments, enforce timeouts and budgets, and show exact effects before approving consequential actions.'), ('Test mixed deployments', 'Cover a current client with a legacy server, a current server with a legacy client, and the selected current path. Record fallback behavior and avoid silently downgrading security or dropping unsupported capabilities.')],
            'outcomes': ['Implement and explain the client’s protocol selection or fallback policy.', 'Keep tool allowlists, argument checks, and approvals outside the model.', 'Test compatibility and failure behavior across supported peers.'],
        },
        '8.12': {
            'title': 'Production MCP Architecture and Upgrades',
            'subtitle': 'Operate versioned MCP servers with capability ownership, safe protocol upgrades, authorization, and observable compatibility.',
            'concepts': [('Registry records compatibility', 'Track owner, server release, protocol revisions, SDK support, transport, authorization method, data classification, and supported capabilities. A registry should make unsupported combinations visible before rollout.'), ('Upgrade both eras safely', 'The 2026-07-28 protocol removes initialize and transport sessions while older revisions retain them. Use staged compatibility tests, canaries, explicit fallback rules, and a deprecation window. Keep application state in explicit application handles when it must survive requests.'), ('Operate the boundary', 'Enforce authentication, authorization, origin and host protections, quotas, and audit at the appropriate server or gateway boundary. Trace caller, server version, protocol revision, method, latency, and outcome without recording secrets or full sensitive payloads.')],
            'outcomes': ['Design a registry entry with protocol and SDK compatibility.', 'Plan a staged upgrade across handshake-era and stateless peers.', 'Define observability and security controls at host, gateway, and server boundaries.'],
        },
    }
    for lesson_id, update in mcp_updates.items():
        lesson = lessons[lesson_id]
        module = modules[lesson['module_id']]
        lesson['title'] = update['title']
        lesson['subtitle'] = update['subtitle']
        lesson['outcomes'] = update['outcomes']
        lesson['core_concepts'] = [{'title': name, 'content': body} for name, body in update['concepts']]
        lesson['meta'] = f"{module['title']} · reviewed 2026"
        concept_block = '\n\n'.join(f'{n}\n{b}' for n, b in update['concepts'])
        lesson['why_it_matters'] = [lesson['subtitle']]
        lesson['questions'] = [
            'Which MCP revisions use the initialize handshake?',
            'What changed in the 2026-07-28 revision?',
            'Why is protocol negotiation not an authorization check?',
            'Which compatibility and fallback behavior should be tested?'
        ]
        lesson['tasks'] = [
            'Build a protocol and SDK compatibility matrix for the peers you support.',
            'Test one current and one handshake-era peer or fixture.'
        ]
        lesson['common_mistakes'] = [
            'Assuming every MCP peer uses initialize and a session ID.',
            'Treating a successful handshake as authorization.',
            'Silently falling back to an older protocol without recording the downgrade.'
        ]
        lesson['production_notes'] = [
            'Log protocol revision, SDK version, transport, method, and outcome without logging credentials.',
            'Test mixed-version peers and define deprecation windows before rollout.',
            'Keep application state and permissions explicit rather than relying on transport sessions.'
        ]
        lesson['checklist'] = [
            'Supported protocol revisions are documented.',
            'Current and legacy compatibility paths are tested.',
            'Tool permissions are enforced outside the model.',
            'Fallback behavior is observable.'
        ]
        step_sets = {
            '8.03': [
                'Identify whether each peer uses the handshake-era or stateless protocol revision.',
                'Choose stdio or Streamable HTTP based on deployment and trust boundaries.',
                'Record protocol revision, SDK version, transport, and supported capabilities.',
                'Draw the request path and show where application state lives.',
                'Test both a current peer and a supported legacy peer.'
            ],
            '8.04': [
                'Read the client SDK version and its supported protocol revisions.',
                'Select explicit negotiation or a tested legacy fallback.',
                'Filter advertised tools through a host-owned allowlist.',
                'Validate arguments, deadlines, and approval before executing calls.',
                'Test unsupported versions, transport errors, and downgrade logging.'
            ],
            '8.12': [
                'Inventory server, SDK, protocol, transport, authorization, and capability versions.',
                'Define the supported peer matrix and a deprecation window.',
                'Test mixed-version clients and servers in a staging environment.',
                'Roll out through a canary while recording protocol-specific errors.',
                'Document rollback and state migration behavior.'
            ],
        }
        lesson['steps'] = step_sets[lesson_id]
        lesson['worked_example'] = [
            f"A team updates {lesson['title'].lower()} by checking peer revisions, documenting compatibility, and proving authorization and error handling before rollout."
        ]
        lesson['code'] = {}
        lesson['pages'] = [
            f"{lesson['title']}\n{lesson['subtitle']}\n{module['title']} · reviewed 2026\n\nWHY THIS LESSON MATTERS\n{lesson['subtitle']}\n\nWHAT YOU WILL BE ABLE TO DO\n" + '\n'.join('• ' + x for x in update['outcomes']) + '\n\nCORE CONCEPTS\n' + concept_block,
            f"{lesson['title']}\nBuild it\n\nWORKED EXAMPLE\nA team connects a host to servers using the protocol revision and transport each peer supports. It records the compatibility decision and verifies authorization and failure handling before publishing the integration.\n\nSTEP BY STEP\n1. Check the peer protocol revision and SDK support.\n2. Select the matching lifecycle or an explicit tested fallback.\n3. Validate advertised capabilities against the host allowlist.\n4. Call a harmless read-only capability and inspect the response.\n5. Test timeout, unsupported version, authorization failure, and shutdown behavior.",
            f"{lesson['title']}\nOperate it\n\nCOMMON MISTAKES\n1. Assuming every MCP peer uses initialize and a session ID.\n2. Treating a successful handshake as authorization.\n3. Silently falling back to an older protocol without recording the downgrade.\n\nPRODUCTION NOTES\n◆ Log protocol revision, SDK version, transport, method, and outcome without logging credentials.\n◆ Test mixed-version peers and define deprecation windows before rollout.\n◆ Keep application state and permissions explicit rather than relying on transport sessions.\n\nCHECKPOINT CHECKLIST\n□ Supported protocol revisions are documented.\n□ Current and legacy compatibility paths are tested.\n□ Tool permissions are enforced outside the model.\n□ Fallback behavior is observable.\n\nSHORT QUESTIONS\n1. Which MCP revisions use the initialize handshake?\n2. What changed in the 2026-07-28 revision?\n3. Why is protocol negotiation not an authorization check?\n\nTASKS\n□ Build a protocol and SDK compatibility matrix for the peers you support.\n□ Test one current and one handshake-era peer or fixture.\n\nCAPSTONE CONNECTION\nThe capstone chooses MCP only when the interoperability benefit justifies its version and operations surface.",
        ]
        nested = next(item for item in modules[lesson['module_id']]['lessons'] if item['id'] == lesson_id)
        for key in ('title', 'subtitle', 'why_it_matters', 'outcomes', 'core_concepts', 'questions', 'tasks', 'common_mistakes', 'production_notes', 'checklist', 'steps', 'worked_example', 'code', 'meta', 'pages'):
            nested[key] = lesson[key]

    optional_phases = {
        '12.06': ('Phase 6 — Choose Workflow or Agent', 'Use deterministic steps by default and add a bounded agent only when model-led action selection solves a measured need.', 'An AI capstone may need no agent. Choose and implement the simplest control flow that meets the product requirements.', ['Compare a fixed workflow with a bounded tool-using agent.', 'State what uncertainty requires model-led action selection.', 'Implement the chosen flow with authorization, stop conditions, and hard budgets.'], [('Workflow first', 'Use ordinary code for known sequences, validation, access checks, and transactions. Use an agent only when its next action genuinely depends on model interpretation.'), ('Bound any agent', 'If one is justified, define tools, schemas, steps, cost, wall-clock limits, stop conditions, and approval for consequential effects.'), ('Evaluate the choice', 'Compare both options on the same cases using task success, invalid actions, tool trajectory, latency, and cost.')]),
        '12.07': ('Phase 7 — Choose Retrieval and Grounding', 'Add RAG only when the task needs private or changing knowledge; choose and evaluate the appropriate evidence path.', 'Retrieval helps with private, frequently changing, or source-citable knowledge, but adds ingestion, permission, freshness, and evaluation work.', ['Decide whether retrieval is needed for the product.', 'If used, enforce source permissions and freshness.', 'Evaluate retrieval and answer quality separately, or record why RAG is omitted.'], [('Choose the right source', 'Use a system of record for transactional facts, retrieval for document knowledge, and model context for small stable instructions.'), ('RAG needs operational controls', 'A RAG path needs provenance, deduplication, access filtering, deletion, freshness, retrieval metrics, and a low-evidence fallback.'), ('Omission is a decision', 'When no external knowledge is needed, show that with a data inventory and evaluation instead of adding synthetic documents.')]),
        '12.08': ('Phase 8 — Choose Tool Integration and MCP', 'Use MCP when interoperability across hosts and servers is valuable; an internal typed interface can be enough for one application boundary.', 'MCP adds a protocol and compatibility surface. It is useful for reusable cross-host capabilities, while a single product may be simpler with an internal contract.', ['Compare an internal tool interface with MCP.', 'If using MCP, state supported protocol versions, authorization, and fallback behavior.', 'Enforce tool scopes, validation, and approval at host and server boundaries.'], [('Interoperability is the use case', 'Choose MCP when independent hosts and servers need a shared capability contract. A typed internal interface may be simpler for one application and service.'), ('Version matters', 'The 2026-07-28 stateless era differs from handshake-era revisions through 2025-11-25. State supported revisions and test mixed peers.'), ('Protocol does not grant permission', 'Authenticate callers, authorize actions, validate arguments, cap runtime, and require approval for consequential side effects regardless of protocol.')]),
    }
    for lesson_id, (title, subtitle, why, outcomes, concepts) in optional_phases.items():
        lesson = lessons[lesson_id]
        module = modules[lesson['module_id']]
        lesson.update({
            'title': title, 'subtitle': subtitle, 'why_it_matters': [why],
            'outcomes': outcomes,
            'core_concepts': [{'title': n, 'content': b} for n, b in concepts],
            'mental_model': subtitle,
            'worked_example': ['Write an ADR, implement the chosen option, and keep an evidence-based no-build decision when the feature is not needed.'],
            'steps': ['State the product requirement this component would satisfy.', 'Compare the simplest viable option with alternatives.', 'Choose using evidence and document a clear no-build decision when appropriate.', 'Implement the chosen interface with validation and failure behavior.', 'Record the evaluation and a trigger for revisiting the decision.'],
            'tasks': ['Implement the selected flow or document why the optional feature is unnecessary.', 'Add the decision and its evidence to the capstone architecture record.'],
            'capstone': 'The capstone integrates this component only when its requirements and evaluation justify it.',
            'common_mistakes': ['Adding a subsystem because its phase name sounds mandatory.', 'Ignoring maintenance, authorization, and operating costs.', 'Failing to record why an optional feature was omitted.'],
            'production_notes': ['Keep optional components behind explicit interfaces.', 'Record the evidence and trigger that would justify changing the decision.', 'Include security and operational ownership in the design review.'],
            'checklist': ['The product requirement is explicit.', 'The simplest viable options were compared.', 'The chosen path has validation and failure behavior.', 'The ADR records evidence and a revisit trigger.'],
            'questions': ['Which requirement does this component satisfy?', 'What simpler option could meet the same requirement?', 'What evidence would justify more complexity?', 'Which security boundary does the choice introduce?'],
            'code': {}, 'meta': f"{module['title']} · architecture decision · reviewed 2026",
        })
        lesson['pages'] = [
            f"{title}\n{subtitle}\n{module['title']} · Capstone decision\n\nWHY THIS LESSON MATTERS\n{why}\n\nWHAT YOU WILL BE ABLE TO DO\n" + '\n'.join('• ' + x for x in outcomes) + '\n\nCORE CONCEPTS\n' + '\n\n'.join(f'{n}\n{b}' for n, b in concepts),
            f"{title}\nBuild it\n\nWORKED EXAMPLE\n{lesson['worked_example'][0]}\n\nSTEP BY STEP\n" + '\n'.join(f'{i}. {x}' for i, x in enumerate(lesson['steps'], 1)),
            f"{title}\nOperate it\n\nCOMMON MISTAKES\n" + '\n'.join(f'{i}. {x}' for i, x in enumerate(lesson['common_mistakes'], 1)) + '\n\nPRODUCTION NOTES\n' + '\n'.join('◆ ' + x for x in lesson['production_notes']) + '\n\nCHECKPOINT CHECKLIST\n' + '\n'.join('□ ' + x for x in lesson['checklist']) + '\n\nSHORT QUESTIONS\n' + '\n'.join(f'{i}. {x}' for i, x in enumerate(lesson['questions'], 1)) + '\n\nTASKS\n' + '\n'.join('□ ' + x for x in lesson['tasks']) + '\n\nCAPSTONE CONNECTION\n' + lesson['capstone'],
        ]
        nested = next(item for item in module['lessons'] if item['id'] == lesson_id)
        for key in ('title', 'subtitle', 'why_it_matters', 'outcomes', 'core_concepts', 'mental_model', 'worked_example', 'steps', 'tasks', 'capstone', 'common_mistakes', 'production_notes', 'checklist', 'questions', 'code', 'meta', 'pages'):
            nested[key] = lesson[key]

    # Delimiters help identify untrusted content but do not prevent injection.
    security_lesson = lessons['8.11']
    nested_security = next(item for item in modules['08']['lessons'] if item['id'] == '8.11')
    for record in (security_lesson, nested_security):
        record['pages'] = [page.replace(
            'Mitigate by treating retrieved text as data: wrap it in delimiters, label its source, and keep high-risk tools out of the model\'s reachable set while untrusted content is present. Detection helps, but capability minimisation is the control that holds.',
            'Label untrusted content and preserve its source, but do not treat delimiters as a security barrier. Enforce tool allowlists, authorization, argument validation, egress limits, and approval in code; capability minimisation limits damage when the model follows malicious content.'
        ) for page in record.get('pages', [])]
        for concept in record.get('core_concepts', []):
            concept['content'] = concept.get('content', '').replace(
                'Mitigate by treating retrieved text as data: wrap it in delimiters, label its source, and keep high-risk tools out of the model\'s reachable set while untrusted content is present. Detection helps, but capability minimisation is the control that holds.',
                'Label untrusted content and preserve its source, but do not treat delimiters as a security barrier. Enforce tool allowlists, authorization, argument validation, egress limits, and approval in code; capability minimisation limits damage when the model follows malicious content.'
            )

    prompt_lesson = lessons['4.02']
    prompt_nested = next(item for item in modules['04']['lessons'] if item['id'] == '4.02')
    old_delimiter_advice = 'Insert them only inside labelled delimiters such as <ticket> or fenced blocks, and state in the system section that content inside those tags is data.'
    safe_delimiter_advice = 'Label and delimit them to make provenance clear, but do not treat delimiters or prompt instructions as a security boundary; enforce permissions and tool limits in application code.'
    for record in (prompt_lesson, prompt_nested):
        for concept in record.get('core_concepts', []):
            concept['content'] = concept.get('content', '').replace(old_delimiter_advice, safe_delimiter_advice)
        record['pages'] = [page.replace(old_delimiter_advice, safe_delimiter_advice) for page in record.get('pages', [])]

    # The capstone should assess architecture decisions, not force every
    # fashionable subsystem into every product. Preserve phase IDs for users'
    # progress, but turn the optional components into evidence-led branches.
    optional_phases = {
        '12.06': {
            'title': 'Phase 6 — Choose Workflow or Agent',
            'subtitle': 'Use deterministic steps by default and add a bounded agent only when model-led action selection solves a measured need.',
            'why': 'A capstone feature may need no agent at all. The purpose of this phase is to select and implement the simplest control flow that meets the product requirements.',
            'outcomes': ['Compare fixed workflows with a bounded tool-using agent.', 'State what uncertainty requires model-led action selection.', 'Implement the chosen control flow with authorization and hard budgets.'],
            'concepts': [('A workflow is a valid AI architecture', 'Use ordinary application code for known sequences, validation, access checks, and transactions. Use an agent when the next action genuinely depends on model interpretation and a bounded tool set.'), ('Bound every agent', 'If an agent is justified, define allowed tools, schema validation, per-run steps, cost and wall-clock limits, stop conditions, and approval for consequential effects. These controls belong in application code.'), ('Evaluate the decision', 'Compare the workflow and agent on the same representative cases. Measure task success, invalid actions, tool trajectory, latency, and cost. Keep the workflow when an agent does not earn its complexity.')],
            'task': 'Implement the selected flow and attach a short ADR comparing the alternative, including evaluation evidence.',
        },
        '12.07': {
            'title': 'Phase 7 — Choose Retrieval and Grounding',
            'subtitle': 'Add RAG only when the task needs private or changing knowledge; choose and evaluate the appropriate evidence path.',
            'why': 'Retrieval is useful for private, frequently changing, or source-citable knowledge. It adds ingestion, permissions, freshness, and evaluation work, so it should solve a named requirement.',
            'outcomes': ['Decide whether retrieval is needed for the product’s knowledge requirements.', 'If used, enforce source permissions and freshness through retrieval.', 'Evaluate retrieval quality separately from answer quality and record an ADR if RAG is omitted.'],
            'concepts': [('Knowledge source determines architecture', 'Use a system of record for transactional facts, retrieval for document knowledge, and model context for small stable instructions. Do not build a vector store when a direct authorized query is more accurate.'), ('RAG needs operational controls', 'A RAG path needs ingestion provenance, deduplication, access filtering, deletion propagation, freshness, retrieval metrics, grounded answer checks, and a low-evidence fallback.'), ('Omission is a decision', 'If the product has no external knowledge requirement, demonstrate that with a data inventory and evaluation. Do not add synthetic documents merely to satisfy a project checklist.')],
            'task': 'Choose direct data access, retrieval, or no external knowledge; implement the choice or document why retrieval is unnecessary.',
        },
        '12.08': {
            'title': 'Phase 8 — Choose Tool Integration and MCP',
            'subtitle': 'Use MCP when interoperability across hosts and servers is valuable; a typed internal interface is enough for a single application boundary.',
            'why': 'MCP adds a protocol and compatibility surface. It is valuable for reusable cross-host capabilities, but a single product may be simpler and safer with an internal typed tool contract.',
            'outcomes': ['Compare an internal tool interface with MCP for the capstone’s integration needs.', 'If MCP is selected, state supported protocol versions, authorization, and compatibility behavior.', 'Keep tool scopes, validation, and human approval enforced by the host and server.'],
            'concepts': [('Interoperability is the use case', 'Choose MCP when independent hosts and servers need a shared capability contract. For one application and one service, a typed internal interface may reduce deployment and versioning cost.'), ('Protocol version is part of the design', 'The 2026-07-28 stateless era differs from handshake-era revisions through 2025-11-25. State which revisions and SDK behavior are supported; test mixed peers and fallback explicitly.'), ('The protocol does not grant permission', 'Authenticate callers and authorize each resource and action. Validate tool arguments, cap output and runtime, and require approval for consequential side effects regardless of protocol.')],
            'task': 'Implement the chosen interface. For MCP, include a supported-version matrix and compatibility test; otherwise document the internal contract and the condition that would trigger MCP adoption.',
        },
    }
    for lesson_id, phase in optional_phases.items():
        lesson = lessons[lesson_id]
        module = modules[lesson['module_id']]
        lesson['title'] = phase['title']
        lesson['subtitle'] = phase['subtitle']
        lesson['why_it_matters'] = [phase['why']]
        lesson['outcomes'] = phase['outcomes']
        lesson['core_concepts'] = [{'title': name, 'content': body} for name, body in phase['concepts']]
        lesson['mental_model'] = phase['subtitle']
        lesson['worked_example'] = [phase['task']]
        lesson['steps'] = ['Write the product requirement this component would satisfy.', 'Compare the simplest viable options and note operational, security, latency, and cost implications.', 'Choose an option using evidence; record a clear no-build decision when the feature is unnecessary.', 'Implement the chosen interface with validation, ownership, and failure behavior.', 'Add the relevant evaluation and document the trigger for revisiting the choice.']
        lesson['tasks'] = [phase['task'], 'Add the decision and its evidence to the capstone architecture record.']
        lesson['capstone'] = phase['task']
        lesson['common_mistakes'] = ['Adding a subsystem because its phase name sounds mandatory.', 'Ignoring maintenance and authorization costs when comparing options.', 'Failing to record why an optional feature was omitted.']
        lesson['production_notes'] = ['Keep optional components behind clear interfaces so later adoption does not require rewriting domain logic.', 'Record the evidence and trigger that would justify changing the decision.', 'Include security and operational ownership in the design review.']
        lesson['checklist'] = ['The product requirement is explicit.', 'The simplest viable option was compared with alternatives.', 'The chosen path has an owner, validation, and failure behavior.', 'The ADR records evidence and a revisit trigger.']
        lesson['questions'] = ['Which requirement does this component satisfy?', 'What simpler option could meet the same requirement?', 'What evidence would justify adopting the more complex option?', 'Which security boundary does the choice introduce?']
        lesson['code'] = {}
        lesson['pages'] = [
            f"{lesson['title']}\n{lesson['subtitle']}\n{module['title']} · Capstone decision\n\nWHY THIS LESSON MATTERS\n{phase['why']}\n\nWHAT YOU WILL BE ABLE TO DO\n" + '\n'.join('• ' + x for x in phase['outcomes']) + '\n\nCORE CONCEPTS\n' + '\n\n'.join(f'{n}\n{b}' for n, b in phase['concepts']),
            f"{lesson['title']}\nBuild it\n\nWORKED EXAMPLE\n{phase['task']}\n\nSTEP BY STEP\n" + '\n'.join(f'{i}. {x}' for i, x in enumerate(lesson['steps'], 1)),
            f"{lesson['title']}\nOperate it\n\nCOMMON MISTAKES\n" + '\n'.join(f'{i}. {x}' for i, x in enumerate(lesson['common_mistakes'], 1)) + '\n\nPRODUCTION NOTES\n' + '\n'.join('◆ ' + x for x in lesson['production_notes']) + '\n\nCHECKPOINT CHECKLIST\n' + '\n'.join('□ ' + x for x in lesson['checklist']) + '\n\nSHORT QUESTIONS\n' + '\n'.join(f'{i}. {x}' for i, x in enumerate(lesson['questions'], 1)) + '\n\nTASKS\n' + '\n'.join('□ ' + x for x in lesson['tasks']) + '\n\nCAPSTONE CONNECTION\n' + phase['task'],
        ]
        lesson['meta'] = f"{module['title']} · architecture decision · reviewed 2026"
        nested = next(item for item in module['lessons'] if item['id'] == lesson_id)
        for key in ('title', 'subtitle', 'why_it_matters', 'outcomes', 'core_concepts', 'mental_model', 'worked_example', 'steps', 'tasks', 'capstone', 'common_mistakes', 'production_notes', 'checklist', 'questions', 'code', 'pages', 'meta'):
            nested[key] = lesson[key]

    # Remove the mandatory multi-agent assumption from the capstone narrative.
    capstone = modules['12']
    capstone['title'] = 'Final Capstone: Build and Review an AI System'
    capstone['project'] = 'Deliver a production AI platform whose architecture is justified by requirements and evaluation evidence. Agents, MCP, and multi-agent orchestration are optional where they solve a demonstrated need.'
    capstone['description'] = 'A reviewable capstone that integrates only the model, retrieval, workflow, tool, security, and deployment components justified by a real product brief.'
    capstone_lesson = lessons['12.09']
    capstone_lesson['capstone'] = SPECS['12.09']['capstone']
    for item in capstone['lessons']:
        if item['id'] == '12.09':
            item['capstone'] = capstone_lesson['capstone']
    for m in data['modules']:
        for item in m['lessons']:
            # Keep every nested lesson synchronized for any transformed record.
            canonical = lessons.get(item['id'])
            if canonical and canonical is not item and item['id'] in SPECS:
                for key in SPECS[item['id']]:
                    item[key] = canonical[key]

    old_capstone_title = 'Final Capstone: Build a Production AI Platform'
    new_capstone_title = capstone['title']
    def refresh_capstone_title(value):
        if isinstance(value, dict):
            return {key: refresh_capstone_title(item) for key, item in value.items()}
        if isinstance(value, list):
            return [refresh_capstone_title(item) for item in value]
        if isinstance(value, str):
            return value.replace(old_capstone_title, new_capstone_title)
        return value
    data = refresh_capstone_title(data)

    foundation = next(lesson for lesson in data['lessons'] if lesson['id'] == '0.01')
    foundation_nested = next(item for item in next(m for m in data['modules'] if m['id'] == '00')['lessons'] if item['id'] == '0.01')
    for record in (foundation, foundation_nested):
        for concept in record.get('core_concepts', []):
            concept['content'] = concept.get('content', '').replace(
                'Every module adds a component to one production AI platform rather than demonstrating an isolated trick.',
                'Each module teaches a component or architecture decision that you can apply to one product brief.'
            ).replace(
                'By the final module you will have authentication, a data layer, retrieval, tool calling, evaluation, tracing, and a deployment runbook.',
                'By the final module you will have a reviewable AI system, and your architecture record will explain which optional components you included or rejected.'
            ).replace(
                'a complete, production-ready AI application',
                'a reviewable AI application whose optional components fit the product brief'
            )
        for term in record.get('key_terms', []):
            if isinstance(term, dict) and term.get('term') == 'Capstone':
                term['definition'] = 'The final project where you design, build, evaluate, and review an AI system, justifying which optional components belong in it.'
        record['pages'] = [re.sub(
            r'By the final module you will have authentication,\s*a data layer,\s*retrieval,\s*tool calling,\s*evaluation,\s*tracing,\s*and a deployment\s+runbook\.',
            'By the final module you will have a reviewable AI system, and your architecture record will explain which optional components you included or rejected.',
            re.sub(
            r'Every module adds a component to one production AI platform rather than demonstrating an isolated trick\.',
            'Each module teaches a component or architecture decision that you can apply to one product brief.',
            page
        )) for page in record.get('pages', [])]

    data['course']['description'] = (
        f"A {len(data['modules'])}-module, {len(data['lessons'])}-lesson AI "
        'engineering course covering Python, backend systems, LLM applications, '
        'multimodal inputs, RAG, agents, MCP, security, evaluation, governance, '
        'and deployment. Lessons and framework examples are versioned for review.'
    )
    for module in data['modules']:
        if module['id'] == '03':
            module['description'] = 'Understand model behavior, generation controls, multimodal inputs, and deployment choices before building AI features.'
        elif module['id'] == '09':
            module['description'] = 'Operate AI systems with security, evaluation, observability, privacy, governance, and controlled change.'
        elif module['id'] == '08':
            module['description'] = 'Build and operate MCP clients and servers across protocol versions, with explicit compatibility, security, and ownership.'
        elif module['id'] == '07':
            module['description'] = 'Design explicit workflows and agent graphs; treat orchestration frameworks as versioned implementation choices.'
        elif module['id'] == '04':
            module['description'] = 'Build reliable model-facing application behavior: prompts, schemas, routing, streaming, context, and request-level cost controls.'
        elif module['id'] == '10':
            module['description'] = 'Package and release AI services; refer to the production module for shared reliability, security, evaluation, and operations practices.'
        elif module['id'] == '11':
            module['description'] = 'Make system-level tradeoffs for scale, reliability, and cost; build on the production controls introduced in Module 09.'
        elif module['id'] == '12':
            module['description'] = 'A reviewable capstone that integrates only the model, retrieval, workflow, tool, security, and deployment components justified by a real product brief.'

    CURRICULUM_PATH.write_text(json.dumps(data, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')

    exercise_path = DATA / 'practice_exercises.json'
    exercises = json.loads(exercise_path.read_text(encoding='utf-8'))
    additions = [
        {'id': 'multimodal-media-validation', 'lesson_id': '3.06', 'title': 'Validate media metadata', 'instructions': 'Implement validate_media(item). Return an error string for unsupported modality, negative or oversized bytes, or missing/invalid duration for audio/video; otherwise return None.', 'starter_code': 'ALLOWED = {"text", "image", "audio", "video"}\n\ndef validate_media(item, max_bytes=1000, max_seconds=60):\n    # TODO: validate modality, size, and audio/video duration.\n    raise NotImplementedError', 'checks_code': 'assert validate_media({"modality":"image","bytes":500}) is None\nassert validate_media({"modality":"image","bytes":2000}) == "invalid_size"\nassert validate_media({"modality":"audio","bytes":20}) == "invalid_duration"\nassert validate_media({"modality":"audio","bytes":20,"duration_seconds":61}) == "invalid_duration"\nassert validate_media({"modality":"video","bytes":20,"duration_seconds":10}) is None\nassert validate_media({"modality":"text","bytes":0}) is None\nassert validate_media({"modality":"archive","bytes":1}) == "unsupported_modality"\nprint("All checks passed.")'},
        {'id': 'model-deployment-decision', 'lesson_id': '3.15', 'title': 'Choose a deployment from constraints', 'instructions': 'Implement choose_deployment(requirements). Choose hosted when it meets latency and privacy constraints; choose self_hosted only when data must remain local and the team has operations capacity; otherwise return needs_review.', 'starter_code': 'def choose_deployment(requirements):\n    # TODO: apply privacy, latency, and operations constraints.\n    raise NotImplementedError', 'checks_code': 'assert choose_deployment({"local_only":False,"hosted_meets_latency":True,"ops_capacity":False}) == "hosted"\nassert choose_deployment({"local_only":True,"hosted_meets_latency":False,"ops_capacity":True}) == "self_hosted"\nassert choose_deployment({"local_only":True,"hosted_meets_latency":True,"ops_capacity":False}) == "needs_review"\nassert choose_deployment({"local_only":False,"hosted_meets_latency":False,"ops_capacity":False}) == "needs_review"\nprint("All checks passed.")'},
        {'id': 'document-evidence-check', 'lesson_id': '4.03', 'title': 'Validate extracted evidence spans', 'instructions': 'Implement valid_extraction(record, text). Require a non-empty string value and a source span whose start/end are valid indices and whose text matches the extracted value after whitespace normalization.', 'starter_code': 'def valid_extraction(record, text):\n    # TODO: validate value and evidence offsets.\n    raise NotImplementedError', 'checks_code': 'text = "Invoice total: 42.00 USD"\nrecord = {"value":"42.00 USD","start":15,"end":24}\nassert valid_extraction(record, text) is True\nassert valid_extraction({"value":"99.00","start":15,"end":20}, text) is False\nassert valid_extraction({"value":"42.00 USD","start":30,"end":39}, text) is False\nassert valid_extraction({"value":"","start":0,"end":0}, text) is False\nprint("All checks passed.")'},
        {'id': 'mcp-protocol-era-selection', 'lesson_id': '8.03', 'title': 'Select MCP compatibility behavior', 'instructions': 'Implement protocol_mode(version). Return stateless for 2026-07-28 and later revisions, handshake for supported earlier dated revisions, and unsupported for malformed or unknown input.', 'starter_code': 'def protocol_mode(version):\n    # TODO: parse YYYY-MM-DD and classify supported protocol eras.\n    raise NotImplementedError', 'checks_code': 'assert protocol_mode("2026-07-28") == "stateless"\nassert protocol_mode("2025-11-25") == "handshake"\nassert protocol_mode("2025-03-26") == "handshake"\nassert protocol_mode("not-a-version") == "unsupported"\nassert protocol_mode("2027-01-01") == "unsupported"\nprint("All checks passed.")'},
        {'id': 'ai-deletion-plan', 'lesson_id': '9.10', 'title': 'Plan deletion across derived stores', 'instructions': 'Implement deletion_targets(record). Return all stores that may contain a document, including source, chunks, embeddings, answer_cache, logs, and eval_data only when the record says evaluation_copy is true. Preserve stable output order.', 'starter_code': 'def deletion_targets(record):\n    # TODO: return every store that may retain this document.\n    raise NotImplementedError', 'checks_code': 'assert deletion_targets({"evaluation_copy":False}) == ["source", "chunks", "embeddings", "answer_cache", "logs"]\nassert deletion_targets({"evaluation_copy":True}) == ["source", "chunks", "embeddings", "answer_cache", "logs", "eval_data"]\nprint("All checks passed.")'},
        {'id': 'ai-risk-control-map', 'lesson_id': '9.13', 'title': 'Map AI risks to controls', 'instructions': 'Implement controls_for(risks), returning unique deterministic controls for prompt_injection, cross_tenant_retrieval, unsafe_output, and unbounded_cost. Do not invent a control for unknown risks.', 'starter_code': 'RISK_CONTROLS = {\n    "prompt_injection": "tool_allowlist",\n    "cross_tenant_retrieval": "tenant_filter",\n    "unsafe_output": "output_validation",\n    "unbounded_cost": "request_budget",\n}\n\ndef controls_for(risks):\n    # TODO: map known risks, keep first occurrence order, ignore unknowns.\n    raise NotImplementedError', 'checks_code': 'assert controls_for(["prompt_injection", "unsafe_output"]) == ["tool_allowlist", "output_validation"]\nassert controls_for(["cross_tenant_retrieval", "cross_tenant_retrieval", "unknown"]) == ["tenant_filter"]\nassert controls_for([]) == []\nprint("All checks passed.")'},
        {'id': 'orchestration-evidence-choice', 'lesson_id': '12.09', 'title': 'Choose the simplest adequate orchestration', 'instructions': 'Implement choose_architecture(evidence). Prefer workflow when the path is fixed. Otherwise keep one_agent unless measured specialist_gain exceeds added_latency_cost and safety checks pass.', 'starter_code': 'def choose_architecture(evidence):\n    # TODO: require evidence before recommending multiple agents.\n    raise NotImplementedError', 'checks_code': 'assert choose_architecture({"fixed_path":True}) == "workflow"\nassert choose_architecture({"fixed_path":False,"specialist_gain":0.2,"added_latency_cost":0.1,"safety_passed":True}) == "multi_agent"\nassert choose_architecture({"fixed_path":False,"specialist_gain":0.1,"added_latency_cost":0.2,"safety_passed":True}) == "one_agent"\nassert choose_architecture({"fixed_path":False,"specialist_gain":0.5,"added_latency_cost":0.1,"safety_passed":False}) == "one_agent"\nprint("All checks passed.")'},
        {'id': 'backend-idempotent-job', 'lesson_id': '2.19', 'title': 'Create or reuse an idempotent job', 'instructions': 'Implement create_or_reuse(key, jobs). Reject a blank key; return the existing job for a repeated key; otherwise add and return one new job id.', 'starter_code': 'def create_or_reuse(key, jobs):\n    # TODO: make repeated submissions safe.\n    raise NotImplementedError', 'checks_code': 'jobs = {}\nassert create_or_reuse("k1", jobs) == ("created", "job-k1")\nassert create_or_reuse("k1", jobs) == ("existing", "job-k1")\nassert len(jobs) == 1\nassert create_or_reuse("", jobs) == ("error", None)\nprint("All checks passed.")'},
        {'id': 'rag-reciprocal-rank', 'lesson_id': '5.17', 'title': 'Score retrieval rank', 'instructions': 'Implement reciprocal_rank(relevant_ids, results, k). Return 1/rank for the first relevant result in the top k, or 0 if none appears. Rank is one-based.', 'starter_code': 'def reciprocal_rank(relevant_ids, results, k):\n    # TODO: find the first relevant result within k.\n    raise NotImplementedError', 'checks_code': 'assert reciprocal_rank({"d2"}, ["d1", "d2", "d3"], 3) == 0.5\nassert reciprocal_rank({"d3"}, ["d1", "d2", "d3"], 2) == 0\nassert reciprocal_rank(set(), ["d1"], 1) == 0\nassert reciprocal_rank({"d1"}, ["d1"], 0) == 0\nprint("All checks passed.")'},
        {'id': 'agent-tool-authorization', 'lesson_id': '6.16', 'title': 'Authorize a tool call outside the model', 'instructions': 'Implement authorize_tool(name, allowed_tools, write_tools, approved). A tool must be allowlisted, and write tools require explicit approval.', 'starter_code': 'def authorize_tool(name, allowed_tools, write_tools, approved):\n    # TODO: enforce host policy deterministically.\n    raise NotImplementedError', 'checks_code': 'allowed = {"search", "send_email"}\nwrites = {"send_email"}\nassert authorize_tool("search", allowed, writes, False) is True\nassert authorize_tool("send_email", allowed, writes, False) is False\nassert authorize_tool("send_email", allowed, writes, True) is True\nassert authorize_tool("delete_all", allowed, writes, True) is False\nprint("All checks passed.")'},
        {'id': 'container-release-readiness', 'lesson_id': '10.07', 'title': 'Check production image readiness', 'instructions': 'Implement release_ready(image). A production image is ready only when it runs as a non-root user, has no baked-in secrets, and declares a health check.', 'starter_code': 'def release_ready(image):\n    # TODO: check all three release requirements.\n    raise NotImplementedError', 'checks_code': 'assert release_ready({"non_root":True,"baked_secrets":False,"healthcheck":True}) is True\nassert release_ready({"non_root":False,"baked_secrets":False,"healthcheck":True}) is False\nassert release_ready({"non_root":True,"baked_secrets":True,"healthcheck":True}) is False\nassert release_ready({"non_root":True,"baked_secrets":False,"healthcheck":False}) is False\nprint("All checks passed.")'},
    ]
    known = {item['id'] for item in exercises}
    exercises.extend(item for item in additions if item['id'] not in known)
    exercise_path.write_text(json.dumps(exercises, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')

    resources_path = DATA / 'dynamoai_resources.json'
    resources = json.loads(resources_path.read_text(encoding='utf-8'))
    resources.update({
        'module:03': {'article': {'title': 'OpenAI API — Images and vision', 'url': 'https://platform.openai.com/docs/guides/images-vision'}, 'audio': {'title': 'OpenAI API — Audio', 'url': 'https://platform.openai.com/docs/guides/audio'}},
        'module:04': {'article': {'title': 'OpenAI API — Structured outputs', 'url': 'https://platform.openai.com/docs/guides/structured-outputs'}, 'evals': {'title': 'OpenAI API — Evaluation best practices', 'url': 'https://platform.openai.com/docs/guides/evals'}},
        'module:05': {'article': {'title': 'PostgreSQL — Full-text search', 'url': 'https://www.postgresql.org/docs/current/textsearch.html'}},
        'module:06': {'article': {'title': 'OWASP GenAI Security Project', 'url': 'https://genai.owasp.org/'}},
        'module:07': {'article': {'title': 'LangGraph — Concepts', 'url': 'https://docs.langchain.com/oss/python/langgraph/overview'}},
        'module:08': {'article': {'title': 'MCP Specification 2026-07-28', 'url': 'https://modelcontextprotocol.io/specification/2026-07-28'}, 'compatibility': {'title': 'MCP protocol versions', 'url': 'https://ts.sdk.modelcontextprotocol.io/v2/protocol-versions'}},
        'module:09': {'security': {'title': 'OWASP Top 10 for LLM Applications', 'url': 'https://genai.owasp.org/initiatives/top-10-for-llm-and-genai/'}, 'governance': {'title': 'NIST Generative AI Profile', 'url': 'https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf'}},
        'module:10': {'article': {'title': 'Docker — Build best practices', 'url': 'https://docs.docker.com/build/building/best-practices/'}},
        'module:11': {'article': {'title': 'OpenTelemetry — Concepts', 'url': 'https://opentelemetry.io/docs/concepts/'}},
        'module:12': {'article': {'title': 'NIST AI RMF Playbook', 'url': 'https://airc.nist.gov/AI_RMF_Knowledge_Base/Playbook'}},
    })
    resources_path.write_text(json.dumps(resources, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')

    print(f"Updated {len(SPECS)} lessons, refreshed MCP/framework/capstone guidance, added {len(additions)} coding exercises, and linked current module resources.")


if __name__ == '__main__':
    main()
