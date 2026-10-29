"""Five-month learning plan and selectable AI engineering capstones."""

MONTHS = [
    {
        'number': 1,
        'title': 'LLM fundamentals, APIs, and structured outputs',
        'summary': 'Treat language models as programmable services with measurable behavior.',
        'modules': ['00', '01', '02', '03'],
        'concepts': ['Context windows and tokens', 'Generation variability and evaluation', 'Image and audio inputs', 'Hosted, self-hosted, and adapted model choices'],
        'weeks': [
            'Set up Python, Git, and a small AI engineering workspace.',
            'Call a hosted or local model through a provider API.',
            'Use system prompts and validate structured JSON responses.',
            'Build a CLI that processes Markdown notes and records cost and latency.',
        ],
        'milestone': 'A dependable Markdown-to-JSON CLI with execution cost and latency logs.',
    },
    {
        'number': 2,
        'title': 'Prompt engineering and systematic evaluation',
        'summary': 'Measure prompt quality with repeatable data and regression checks.',
        'modules': ['04'],
        'concepts': ['Prompt design and versioning', 'Golden datasets of 30–50 examples', 'Assertions and quality metrics', 'GitHub Actions evaluation gates'],
        'weeks': [
            'Define the task, expected behavior, and failure cases.',
            'Create a curated golden dataset of representative requests.',
            'Score correctness, latency, and cost with explicit assertions.',
            'Run the evaluation suite automatically for prompt changes in GitHub Actions.',
        ],
        'milestone': 'A prompt regression harness that reports quality and blocks a failing CI run.',
    },
    {
        'number': 3,
        'title': 'Embeddings, vector databases, and RAG',
        'summary': 'Ground model answers in private or domain-specific information.',
        'modules': ['05'],
        'concepts': ['Chunking and embeddings', 'Permission-aware vector and keyword search', 'Retrieval and answer evaluation', 'Freshness, deletion, citations, and abstention'],
        'weeks': [
            'Prepare documents and compare chunk sizes and overlap.',
            'Create embeddings and index content in a vector store.',
            'Add keyword search, hybrid retrieval, and reranking.',
            'Return cited answers and abstain when evidence is weak.',
        ],
        'milestone': 'A domain Q&A pipeline that retrieves useful evidence and cites its sources.',
    },
    {
        'number': 4,
        'title': 'Workflows, agents, tools, and MCP',
        'summary': 'Choose the simplest control flow that works; use MCP when interoperability justifies its protocol surface.',
        'modules': ['06', '07', '08'],
        'concepts': ['Function calling and ReAct loops', 'State and memory', 'MCP clients and servers', 'Retries, tool errors, and human approval'],
        'weeks': [
            'Define tools with strict input and output schemas.',
            'Compare a deterministic workflow with a bounded agent using the same evaluation cases.',
            'Use an internal tool contract or MCP based on interoperability needs; test supported protocol versions.',
            'Recover from tool errors and require approval for consequential actions.',
        ],
        'milestone': 'A measured workflow or bounded assistant with scoped tools and approval for consequential actions.',
    },
    {
        'number': 5,
        'title': 'Production, observability, and deployment',
        'summary': 'Ship a service that can be operated, measured, and safely changed.',
        'modules': ['09', '10', '11', '12'],
        'concepts': ['FastAPI and Pydantic', 'Docker and deployment', 'Tracing, token usage, and latency', 'AI risk, privacy, retention, and incident response'],
        'weeks': [
            'Wrap the AI workflow in a validated API service.',
            'Containerize the service and its supporting dependencies.',
            'Add structured logs, request traces, token usage, latency metrics, and a data-retention plan.',
            'Deploy with rate limits, caching, health checks, and an operations runbook.',
        ],
        'milestone': 'A deployed, containerized AI service with error handling and production monitoring.',
    },
]

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
