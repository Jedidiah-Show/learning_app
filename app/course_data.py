"""Learning-plan pacing tracks and selectable AI engineering capstones.

Tracks describe available study time; beginner/experienced routes describe
prior knowledge. All tracks cover every lesson and module project.
"""

TRACKS = {
    'steady': {
        'id': 'steady',
        'label': '12-month steady',
        'range': '12 months',
        'description': (
            'The long plan at roughly 10 hours per week. Choose it for the time '
            'you have, not for your experience; prior knowledge is a separate '
            'question and never shortens the projects you must build.'
        ),
        'months': 12,
        'milestones': [
            {'number': 1, 'title': 'Orientation and AI foundations', 'summary': 'Understand the work, set up your workspace, and learn the basic vocabulary.', 'modules': ['00'], 'concepts': ['What AI engineers build', 'Tools and learning habits'], 'weeks': ['Set up your workspace and run a first command.', 'Learn the system map and key vocabulary.', 'Sketch a small AI product.', 'Review and explain the ideas in your own words.'], 'milestone': 'A working workspace and a one-page AI system sketch.'},
            {'number': 2, 'title': 'Python foundations', 'summary': 'Build confidence with Python data, functions, files, and debugging.', 'modules': ['01'], 'concepts': ['Core Python', 'Files and data', 'Debugging and tests'], 'weeks': ['Practice values and collections.', 'Write functions and read files.', 'Debug small failures and add tests.', 'Complete the Python project.'], 'milestone': 'A tested Python utility in a clean repository.'},
            {'number': 3, 'title': 'Backend engineering', 'summary': 'Build a small API and learn how applications store and validate data.', 'modules': ['02'], 'concepts': ['HTTP and JSON', 'Validation', 'Persistence'], 'weeks': ['Trace a browser request.', 'Build endpoints and validate input.', 'Store data and handle errors.', 'Complete the backend project.'], 'milestone': 'A tested API with persistent data.'},
            {'number': 4, 'title': 'LLM fundamentals', 'summary': 'Learn model behavior, choices, context, and evaluation.', 'modules': ['03'], 'concepts': ['Model behavior', 'Tokens and context', 'Evaluation'], 'weeks': ['Call a model through an API.', 'Compare output quality and cost.', 'Practice structured results.', 'Complete the LLM project.'], 'milestone': 'A model-backed tool with measured behavior.'},
            {'number': 5, 'title': 'LLM application engineering', 'summary': 'Build prompts and application logic that can be tested.', 'modules': ['04'], 'concepts': ['Prompt design', 'Validation', 'Regression checks'], 'weeks': ['Define a task and failure cases.', 'Create examples for evaluation.', 'Build a validated feature.', 'Add regression checks.'], 'milestone': 'An AI feature with repeatable quality checks.'},
            {'number': 6, 'title': 'Retrieval and RAG', 'summary': 'Find evidence in documents and use it to ground answers.', 'modules': ['05'], 'concepts': ['Embeddings', 'Search', 'Citations'], 'weeks': ['Prepare a small document set.', 'Index and retrieve relevant passages.', 'Generate cited answers.', 'Measure retrieval quality.'], 'milestone': 'A RAG pipeline with citations and evaluation.'},
            {'number': 7, 'title': 'AI agents', 'summary': 'Give a model tools within explicit limits and compare it with a workflow.', 'modules': ['06'], 'concepts': ['Tool calling', 'Control flow', 'Approvals'], 'weeks': ['Define a narrow tool.', 'Build a deterministic workflow.', 'Compare it with a bounded agent.', 'Add approval and failure handling.'], 'milestone': 'A bounded workflow or agent with tests.'},
            {'number': 8, 'title': 'Orchestration', 'summary': 'Learn when multiple agents or orchestration add value.', 'modules': ['07'], 'concepts': ['Coordination', 'State', 'Evaluation'], 'weeks': ['Map the task and roles.', 'Build the simplest working flow.', 'Measure coordination overhead.', 'Complete the module project.'], 'milestone': 'An evaluated orchestration design.'},
            {'number': 9, 'title': 'MCP and tool integration', 'summary': 'Connect tools using explicit contracts and permissions.', 'modules': ['08'], 'concepts': ['MCP', 'Permissions', 'Recovery'], 'weeks': ['Explore client and server roles.', 'Connect a scoped tool.', 'Test permissions and failures.', 'Document the integration.'], 'milestone': 'A tested tool integration with scoped permissions.'},
            {'number': 10, 'title': 'Production AI engineering', 'summary': 'Make AI services observable, cost-aware, and supportable.', 'modules': ['09'], 'concepts': ['Tracing', 'Budgets', 'Privacy'], 'weeks': ['Add useful logs and traces.', 'Measure latency and cost.', 'Add safeguards and a runbook.', 'Complete the production project.'], 'milestone': 'An observable service with an operations runbook.'},
            {'number': 11, 'title': 'Deployment and system design', 'summary': 'Package and deploy a service, then explain the design choices.', 'modules': ['10', '11'], 'concepts': ['Containers', 'Releases', 'Architecture trade-offs'], 'weeks': ['Package the service.', 'Add health checks and configuration.', 'Write design and failure notes.', 'Complete both module projects.'], 'milestone': 'A deployable service and a reviewed design.'},
            {'number': 12, 'title': 'Capstone and portfolio', 'summary': 'Integrate your skills into one defensible, production-minded project.', 'modules': ['12'], 'concepts': ['Scope', 'Evaluation', 'Operations', 'Presentation'], 'weeks': ['Choose a capstone and define success.', 'Build the end-to-end system.', 'Evaluate safety, quality, and operations.', 'Prepare evidence and present your decisions.'], 'milestone': 'A capstone with passing checks and evaluation evidence.'},
        ],
    },
    'standard': {
        'id': 'standard',
        'label': '10-month standard',
        'range': '9–12 months',
        'description': (
            'A roughly 12-hour weekly average for learners who are working or '
            'studying alongside the course. Individual months vary with project load.'
        ),
        'months': 10,
        'milestones': [
            {
                'number': 1,
                'title': 'Foundations and Python fluency',
                'summary': 'Build a reliable workspace, then learn Python by writing and debugging small programs.',
                'modules': ['00', '01'],
                'concepts': ['Terminal, Git, and a reproducible workspace', 'Data, loops, functions, and files', 'Reading tracebacks and testing'],
                'weeks': [
                    'Set up Python, Git, and a small AI engineering workspace.',
                    'Practice lists, dictionaries, functions, files, and errors.',
                    'Complete the Module 0 and Module 1 projects with repository evidence.',
                    'Review weak Python topics before starting backend engineering.',
                ],
                'milestone': 'A tested Python toolkit with a clean repository and readable commit history.',
            },
            {
                'number': 2,
                'title': 'Backend engineering',
                'summary': 'Expose reliable HTTP services with validation, persistence, and tests.',
                'modules': ['02'],
                'concepts': ['HTTP and JSON contracts', 'FastAPI and Pydantic validation', 'SQL persistence and migrations', 'API tests and error handling'],
                'weeks': [
                    'Build and test a small JSON API.',
                    'Add validation, database persistence, and migrations.',
                    'Handle failures and verify behaviour with automated tests.',
                    'Complete the backend module project and checks.',
                ],
                'milestone': 'A tested backend API that stores data and fails safely.',
            },
            {
                'number': 3,
                'title': 'LLM fundamentals',
                'summary': 'Treat language models as programmable services with measurable behaviour.',
                'modules': ['03'],
                'concepts': ['Tokens and context windows', 'Hosted, open-weight, and adapted models', 'Reasoning and fine-tuning decisions', 'Structured outputs and evaluation'],
                'weeks': [
                    'Call a hosted or local model through an API.',
                    'Compare model choices, cost, latency, and reliability.',
                    'Use system prompts and validate structured JSON responses.',
                    'Complete the LLM fundamentals project with a checks link.',
                ],
                'milestone': 'A model-backed tool with cost, latency, and output-quality evidence.',
            },
            {
                'number': 4,
                'title': 'LLM application engineering',
                'summary': 'Design prompts, tools, and application boundaries that remain testable.',
                'modules': ['04'],
                'concepts': ['Prompt versioning', 'Schema-constrained outputs', 'Application state and errors', 'Evaluation-driven iteration'],
                'weeks': [
                    'Define a task and its failure cases.',
                    'Create a small golden dataset and assertions.',
                    'Build a prompt-driven application with validation.',
                    'Add regression checks to CI.',
                ],
                'milestone': 'An evaluated LLM application that blocks a failing prompt change.',
            },
            {
                'number': 5,
                'title': 'Embeddings, vector databases, and RAG',
                'summary': 'Ground answers in private evidence and abstain when evidence is weak.',
                'modules': ['05'],
                'concepts': ['Chunking and embeddings', 'Hybrid retrieval and reranking', 'Permission-aware search', 'Citations and retrieval evaluation'],
                'weeks': [
                    'Prepare documents and compare chunking strategies.',
                    'Create embeddings and index content.',
                    'Add keyword search, hybrid retrieval, and reranking.',
                    'Return cited answers and abstain below a confidence threshold.',
                ],
                'milestone': 'A RAG pipeline that retrieves useful evidence and cites its sources.',
            },
            {
                'number': 6,
                'title': 'AI agents',
                'summary': 'Use the simplest control flow that works before adding autonomy.',
                'modules': ['06'],
                'concepts': ['Tool schemas and function calling', 'Bounded ReAct loops', 'State, memory, and retries', 'Computer-use risks'],
                'weeks': [
                    'Define tools with strict input and output schemas.',
                    'Compare a deterministic workflow with a bounded agent.',
                    'Add retries, tool-error recovery, and approval checkpoints.',
                    'Complete the agent module project with evidence.',
                ],
                'milestone': 'A measured, bounded agent or workflow with scoped tools.',
            },
            {
                'number': 7,
                'title': 'Agent orchestration and MCP',
                'summary': 'Coordinate agents and tools only when evaluation justifies the added complexity.',
                'modules': ['07', '08'],
                'concepts': ['Orchestration patterns', 'Agent-to-agent communication', 'MCP clients and servers', 'Protocol versions and permissions'],
                'weeks': [
                    'Choose a single agent, workflow, or split architecture using evidence.',
                    'Test supported MCP protocol versions and permissions.',
                    'Add durable state, approval, and recovery.',
                    'Complete the orchestration and MCP projects.',
                ],
                'milestone': 'A tested orchestration or MCP integration with explicit boundaries.',
            },
            {
                'number': 8,
                'title': 'Production AI engineering',
                'summary': 'Operate an AI service with tracing, budgets, safeguards, and incident readiness.',
                'modules': ['09'],
                'concepts': ['Structured logs and traces', 'Token and latency budgets', 'Rate limits, caching, and queues', 'Privacy, retention, and incidents'],
                'weeks': [
                    'Add request traces, token usage, and latency metrics.',
                    'Set rate limits, caches, and cost budgets.',
                    'Document retention, abuse handling, and an incident runbook.',
                    'Complete the production module project.',
                ],
                'milestone': 'A monitored AI service with budgets and an operations runbook.',
            },
            {
                'number': 9,
                'title': 'Deployment and system design',
                'summary': 'Package, deploy, and explain a production AI system.',
                'modules': ['10', '11'],
                'concepts': ['Containers and Compose', 'Health checks and release process', 'Architecture trade-offs', 'Cost and failure analysis'],
                'weeks': [
                    'Containerize the service and supporting dependencies.',
                    'Add health checks, configuration, and a release process.',
                    'Write an architecture decision record and failure analysis.',
                    'Complete the deployment and system-design projects.',
                ],
                'milestone': 'A deployable service and a defensible system design review.',
            },
            {
                'number': 10,
                'title': 'Final capstone',
                'summary': 'Integrate the course into one production-grade AI system and defend the evidence.',
                'modules': ['12'],
                'concepts': ['Capstone scope and evidence', 'End-to-end evaluation', 'Security and operations review', 'Portfolio presentation'],
                'weeks': [
                    'Choose one required capstone and define acceptance criteria.',
                    'Build the end-to-end workflow with automated checks.',
                    'Run evaluation, security, and operations reviews.',
                    'Submit the repository, public checks, and project defence.',
                ],
                'milestone': 'A deployed capstone with passing checks, evaluation evidence, and a clear defence.',
            },
        ],
    },
    'accelerated': {
        'id': 'accelerated',
        'label': '5-month intensive',
        'range': '≈24 focused hours/week',
        'description': (
            'An intensive plan for learners who can reserve roughly 24 focused '
            'hours every week. Some months need more time because projects are '
            'uneven; keep the same projects, placement rules, and assessment '
            'gates.'
        ),
        'months': 5,
        'milestones': [
            {
                'number': 1,
                'title': 'Foundations, Python, and backend services',
                'summary': 'Build the workspace, learn Python, and ship a tested backend API.',
                'modules': ['00', '01', '02'],
                'concepts': ['Python and tooling', 'HTTP and data modelling', 'Tests and error handling', 'Project evidence'],
                'weeks': [
                    'Set up Python, Git, and a small AI engineering workspace.',
                    'Practice Python by completing the runnable exercises.',
                    'Build and test a small JSON API with persistence.',
                    'Complete Modules 0–2 projects with repository checks.',
                ],
                'milestone': 'A tested Python and backend foundation with passing checks.',
            },
            {
                'number': 2,
                'title': 'LLM fundamentals and application engineering',
                'summary': 'Call models reliably, constrain outputs, and evaluate prompt changes.',
                'modules': ['03', '04'],
                'concepts': ['Model selection and cost', 'Structured outputs', 'Prompt evaluation', 'Application validation'],
                'weeks': [
                    'Call a hosted or local model and log cost and latency.',
                    'Build a schema-validated application and golden dataset.',
                    'Add regression checks for prompt changes.',
                    'Complete the LLM projects with automated checks.',
                ],
                'milestone': 'An evaluated LLM application that blocks a failing prompt change.',
            },
            {
                'number': 3,
                'title': 'RAG and agents',
                'summary': 'Ground answers with retrieval and compare workflows with bounded agents using evaluation evidence.',
                'modules': ['05', '06'],
                'concepts': ['Embeddings and retrieval', 'Tool schemas', 'Bounded autonomy', 'State and approvals'],
                'weeks': [
                    'Embed and retrieve relevant passages for grounded answers.',
                    'Compare a workflow with a bounded agent on the same cases.',
                    'Add approval checkpoints and durable state.',
                    'Complete the RAG and agent projects.',
                ],
                'milestone': 'A measured agent or workflow with explicit safety boundaries.',
            },
            {
                'number': 4,
                'title': 'Agents, MCP, and production',
                'summary': 'Package tool integrations, run orchestration, and operate an observable AI service.',
                'modules': ['07', '08', '09'],
                'concepts': ['Tool schemas', 'Bounded autonomy', 'State and approvals', 'MCP permissions', 'Tracing and token budgets', 'Rate limits and caching', 'Privacy and incident response'],
                'weeks': [
                    'Build an MCP client or server with scoped permissions.',
                    'Add structured logs, traces, and cost budgets.',
                    'Add rate limits, caching, and an incident runbook.',
                    'Complete the orchestration, MCP, and production projects.',
                ],
                'milestone': 'A permissioned MCP integration and a monitored AI service.',
            },
            {
                'number': 5,
                'title': 'Deployment, system design, and capstone',
                'summary': 'Deploy the system, defend its architecture, and complete the required capstone.',
                'modules': ['10', '11', '12'],
                'concepts': ['Containers and release process', 'Architecture trade-offs', 'End-to-end evaluation', 'Portfolio defence'],
                'weeks': [
                    'Containerize the service and add health checks.',
                    'Write the architecture decision record and failure analysis.',
                    'Run evaluation, security, and operations reviews.',
                    'Submit the capstone repository and public passing checks.',
                ],
                'milestone': 'A deployed capstone with passing checks and a defended design.',
            },
        ],
    },
}

TRACK_IDS = tuple(TRACKS)
MONTHS = TRACKS['accelerated']['milestones']


def track_for(track_id):
    """Return a known track, falling back to the standard plan."""
    return TRACKS.get(track_id) or TRACKS['standard']


def milestones_for(track_id):
    return track_for(track_id)['milestones']


def track_label(track_id):
    track = track_for(track_id)
    return f"{track['label']} ({track['range']})"


# Two separate onboarding questions. Prior knowledge decides which route through
# Module 0 is worth showing; available hours decide the pace. Asking them as one
# question is what made the app assume a beginner needs more months.
SKILL_LEVELS = [
    {
        'id': 'new',
        'label': 'New to programming',
        'description': 'You have not written a program that runs, or you have only followed tutorials.',
    },
    {
        'id': 'some_programming',
        'label': 'Some programming',
        'description': 'You have written scripts or small programs, but not built, tested, and deployed an application.',
    },
    {
        'id': 'experienced',
        'label': 'Experienced',
        'description': 'You ship software already and want the AI-specific lessons and the module projects.',
    },
]

PACE_CHOICES = [
    {'id': '4-8', 'label': '4 to 8 hours a week', 'hours': 6, 'track': 'steady'},
    {'id': '10-12', 'label': '10 to 12 hours a week', 'hours': 11, 'track': 'standard'},
    {'id': '15-20', 'label': '15 to 20 hours a week', 'hours': 17, 'track': 'standard'},
    {'id': '24+', 'label': '24 hours or more a week', 'hours': 24, 'track': 'accelerated'},
]

# Setup checks for the guided start in lesson 0.01. The learner attests to each
# one; the app only records that they did, so a stuck beginner is visible on the
# dashboard instead of looking absent.
SETUP_CHECKS = [
    {
        'id': 'terminal',
        'label': 'You can open a terminal in your project folder',
        'command': 'pwd',
        'expect': 'It prints the folder you are standing in. Every command below runs from there.',
    },
    {
        'id': 'python',
        'label': 'Python is installed',
        'command': 'python3 --version',
        'expect': 'Python 3.10 or newer. On Windows the command is usually `python --version`. '
                  'If it is not found, install Python from python.org, then reopen the terminal.',
    },
    {
        'id': 'editor',
        'label': 'An editor can open that folder',
        'command': 'code .',
        'expect': 'Your editor opens with the folder in its sidebar. Any plain-text editor works for this course.',
    },
    {
        'id': 'git',
        'label': 'Git is installed',
        'command': 'git --version',
        'expect': 'git version 2.x. You need Git to publish every module project.',
    },
    {
        'id': 'first_program',
        'label': 'You have run your first Python program',
        'command': 'python3 -c "print(\'Hello, AI engineering!\')"',
        'expect': 'Hello, AI engineering! appears on the next line. That is a program running on your machine.',
    },
]


def skill_level_for(value):
    for level in SKILL_LEVELS:
        if level['id'] == value:
            return level
    return None


def pace_choice_for(value):
    for choice in PACE_CHOICES:
        if choice['id'] == value:
            return choice
    return None


def recommend_track(weekly_hours):
    """Pick a pace from hours available, never from assumed experience."""
    if not isinstance(weekly_hours, int) or isinstance(weekly_hours, bool):
        return None
    if weekly_hours < 9:
        return 'steady'
    if weekly_hours < 22:
        return 'standard'
    return 'accelerated'


REQUIRED_PROJECTS = [
    {
        'id': 'production-rag',
        'title': 'High-precision production RAG engine',
        'summary': 'Build a document Q&A engine with hybrid search, reranking, permission-aware retrieval, citations, and a clear low-confidence fallback.',
        'stack': 'Python · FastAPI · pgvector or Qdrant · SentenceTransformers · Pydantic',
        'evidence': ['Ingest PDF, Markdown, and tabular sources', 'Enforce role-based access in retrieval', 'Cite exact sources and abstain when context is insufficient'],
    },
    {
        'id': 'multi-tool-agent-mcp',
        'title': 'Bounded tool-using assistant or MCP server',
        'summary': 'Build a bounded workflow or assistant with scoped tools and approval for consequential actions. Use MCP for interoperability; use multiple agents only when evaluation evidence justifies the added coordination.',
        'stack': 'Python · provider SDKs · Asyncio · Docker · optional MCP',
        'evidence': ['Define local or remote tools with strict schemas', 'Recover from failed or invalid tool calls', 'Demonstrate approval checkpoints and durable application state', 'Record evidence for choosing workflow, single agent, MCP, or an optional multi-agent split'],
    },
    {
        'id': 'evaluation-harness',
        'title': 'Continuous evaluation and regression harness',
        'summary': 'Benchmark an LLM workflow against a golden dataset and prevent quality or cost regressions from shipping.',
        'stack': 'Pytest · DeepEval or Ragas · GitHub Actions · Pandas or DuckDB',
        'evidence': ['Score correctness, context recall, faithfulness, and latency', 'Run evaluation on every pull request', 'Compare quality, latency, and cost across model backends'],
    },
    {
        'id': 'observable-microservice',
        'title': 'Containerized AI microservice with observability',
        'summary': 'Ship an AI workflow as a deployable API with structured logs, request tracing, token usage, rate limits, and local dependencies.',
        'stack': 'FastAPI · Docker Compose · OpenTelemetry, Langfuse, or Phoenix · Redis · Uvicorn',
        'evidence': ['Validate requests and model output with schemas', 'Trace model and tool spans with token and latency data', 'Start the app, vector store, and cache with one command'],
    },
]

PROJECT_BY_ID = {project['id']: project for project in REQUIRED_PROJECTS}
