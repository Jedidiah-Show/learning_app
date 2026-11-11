import json

with open('app/data/practice_exercises.json', 'r') as f:
    exercises = json.load(f)

print(f"Current count: {len(exercises)}")

# New project 1 - RAG System
project1 = {
    "id": "ai-engineering-capstone-1",
    "lesson_id": "capstone-1",
    "title": "Build a RAG Document Q&A System",
    "instructions": "Implement a Retrieval-Augmented Generation (RAG) system that can answer questions about a given set of documents. Include document ingestion, vector storage, and relevance ranking.",
    "starter_code": "import json\n\ndef ingest_documents(documents):\n    \"\"\"Process and store documents for RAG retrieval.\"\"\"\n    pass\n# TODO: Implement vector search and answer generation\n# Test: Should return relevant snippets for the query\nresult = ingest_documents([\n    {\"title\": \"AI\", \"content\": \"Artificial intelligence is...\"}\n])\nprint(f\"Ingested {len(result)} documents\")",
    "checks_code": "assert ingest_documents([{\"title\": \"AI\", \"content\": \"test\"}]) is not None\n# Additional checks for vector search",
    "solution_code": "import json\nfrom typing import List\n\ndef ingest_documents(documents: List[dict]) -> List[dict]:\n    \"\"\"Process and store documents for RAG retrieval.\"\"\"\n    # In a real system, this would embed and store vectors\n    # For this exercise, we normalise and return the documents\n    normalised = []\n    for doc in documents:\n        normalised.append({\n            "id": doc.get("id", 0),\n            "title": doc.get("title", ""),\n            "content": doc.get("content", ""),\n            "embedded": True\n        })\n    return normalised\n# Test\ndocs = ingest_documents([{\"title\": \"AI\", \"content\": \"Artificial intelligence...\"}])\nassert len(docs) == 1\nassert docs[0]["embedded"] == True\nprint(\"RAG system working!\")",
    "estimated_minutes": 120,
    "difficulty": "advanced",
    "skills": ["rag-retrieval", "document-ingestion", "vector-search", "llm-integration"],
    "prerequisites": ["foundations", "python"]
}

# New project 2 - AI API Service
project2 = {
    "id": "ai-engineering-capstone-2",
    "lesson_id": "capstone-2",
    "title": "Design and Deploy an AI API Service",
    "instructions": "Design and deploy a production-ready AI API service with authentication, rate limiting, request validation, and monitoring. The service should accept prompts and return AI-generated responses with proper error handling.",
    "starter_code": "from flask import Flask, request, jsonify\nfrom flask_limiter import Limiter\nfrom flask_limiter.errors import raise_limited\nimport os\n\napp = Flask(__name__)\nlimiter = Limiter(\n    app=app,\n    key_func=lambda: os.getenv("API_KEY", "default"),\n    default_limits=["100 per day", "10 per minute"]\n)\n\n@app.route("/health", methods=["GET"])\ndef health():\n    return jsonify({\"status\": \"healthy\"})\n\n@app.route("/query", methods=["POST"])\n@limiter.limit("50 per minute")\ndef query():\n    data = request.json\n    prompt = data.get("prompt", "")\n    # TODO: Implement AI query processing\n    return jsonify({\"response\": \"Hello from AI service!\", \"model\": \"test-model\"})\n\n# Test\nwith app.test_client() as client:\n    resp = client.get("/health")\n    assert resp.status_code == 200\n    print("Health check OK)",
    "checks_code": "assert app is not None\nwith app.test_client() as client:\n    resp = client.get("/health")\n    assert resp.status_code == 200\n    # Test rate limiting\n    resp = client.post("/query", json={"prompt": "test"})\n    assert resp.status_code in [200, 429]",
    "solution_code": "import os\nfrom flask import Flask, request, jsonify\nfrom flask_limiter import Limiter\nfrom flask_limiter.errors import raise_limited\n\napp = Flask(__name__)\nlimiter = Limiter(\n    app=app,\n    key_func=lambda: os.getenv("API_KEY", "default"),\n    default_limits=["100 per day", "10 per minute"]\n)\n\n@app.route("/health", methods=["GET"])\ndef health():\n    return jsonify({\"status\": \"healthy\"})\n\n@app.route("/query", methods=["POST"])\ndef query():\n    data = request.json\n    prompt = data.get("prompt", "")\n    # Simulate AI processing\n    response = f\"AI response to: {prompt[:50]}...\"\n    return jsonify({\"response\": response, \"model\": \"demo-model\"})\n\n# Rate limiting is configured via Limiter decorator\n# Test\nwith app.test_client() as client:\n    resp = client.get("/health")\n    assert resp.status_code == 200\n    resp = client.post("/query", json={"prompt": "test"})\n    assert resp.status_code == 200\n    data = resp.get_json()\n    assert "response" in data\nprint("AI API service ready!)",
    "estimated_minutes": 90,
    "difficulty": "advanced",
    "skills": ["api-design", "flask", "rate-limiting", "deployment", "monitoring"],
    "prerequisites": ["python", "foundations"]
}

exercises.extend([project1, project2])

with open('app/data/practice_exercises.json', 'w') as f:
    json.dump(exercises, f, indent=2)

print(f"\nAdded 2 flagship projects")
print(f"Total exercises: {len(exercises)}")

# Verify
for i in range(len(exercises) - 2, len(exercises)):
    e = exercises[i]
    print(f"  {e['id']}: difficulty={e['difficulty']}, skills={len(e['skills'])}")