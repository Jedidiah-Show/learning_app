"""Five-month learning plan and selectable AI engineering capstones."""

MONTHS = [
    {
        'number': 1,
        'title': 'LLM fundamentals, APIs, and structured outputs',
        'summary': 'Treat language models as programmable services with measurable behavior.',
        'modules': ['00', '01', '02', '03'],
        'concepts': ['Context windows and tokens', 'Temperature and system prompts', 'Provider APIs and local Ollama endpoints', 'Schema-validated JSON, cost, and latency'],
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
        'concepts': ['Chunking and embeddings', 'Vector search with pgvector or Qdrant', 'Hybrid BM25 and vector retrieval', 'Reranking, citations, and abstention'],
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
        'title': 'Agents, tools, and Model Context Protocol',
        'summary': 'Build stateful workflows that use tools with clear trust boundaries.',
        'modules': ['06', '07', '08'],
        'concepts': ['Function calling and ReAct loops', 'State and memory', 'MCP clients and servers', 'Retries, tool errors, and human approval'],
        'weeks': [
            'Define tools with strict input and output schemas.',
            'Build a bounded agent loop with persistent task state.',
            'Expose or consume tools through an MCP server or client.',
            'Recover from tool errors and require approval for consequential actions.',
        ],
        'milestone': 'A multi-step assistant that uses custom tools and pauses for human approval when needed.',
    },
    {
        'number': 5,
        'title': 'Production, observability, and deployment',
        'summary': 'Ship a service that can be operated, measured, and safely changed.',
        'modules': ['09', '10', '11', '12'],
        'concepts': ['FastAPI and Pydantic', 'Docker and deployment', 'Tracing, token usage, and latency', 'Rate limits, caching, and error handling'],
        'weeks': [
            'Wrap the AI workflow in a validated API service.',
            'Containerize the service and its supporting dependencies.',
            'Add structured logs, request traces, token usage, and latency metrics.',
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
        'title': 'Autonomous multi-tool agent or MCP server',
        'summary': 'Create a stateful assistant that plans work, calls custom tools, handles tool failures, and asks for approval before consequential actions.',
        'stack': 'Python · LangGraph or LiteLLM · Asyncio · Docker · MCP',
        'evidence': ['Define local or remote tools with strict schemas', 'Recover from failed or invalid tool calls', 'Demonstrate approval checkpoints and session state'],
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
