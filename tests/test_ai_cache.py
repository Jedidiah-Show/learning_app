"""Tests for SHA-256 prompt matching, semantic normalization, and AI response caching."""

import unittest
from unittest.mock import patch

from app import create_app
from app.ai_cache import (
    clear_ai_cache,
    compute_prompt_hash,
    get_cached_response,
    get_semantic_cached_response,
    set_cached_response,
)
from app.gemini import generate_json


class AICacheTests(unittest.TestCase):
    def setUp(self):
        clear_ai_cache()
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            GEMINI_API_KEY='test-key',
            AI_CACHE_ENABLED=True,
        )
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        clear_ai_cache()
        self.ctx.pop()

    def test_compute_prompt_hash_normalizes_whitespace(self):
        h1 = compute_prompt_hash("Generate a quiz question for Python", "flash")
        h2 = compute_prompt_hash("  Generate   a  quiz question for Python\n\n", "flash")
        self.assertEqual(h1, h2)

    def test_cache_hit_bypasses_remote_network_call(self):
        prompt = "Create 5 multiple choice questions"
        payload = {"questions": [{"id": 1, "text": "What is Python?"}]}
        set_cached_response(prompt, payload, model="flash")

        # Even with mocked provider that would raise an error, cached response is returned
        with patch("app.gemini._generate_with_gemini") as mock_gemini:
            result = generate_json(prompt, model="flash", use_cache=True)
            self.assertEqual(result, payload)
            mock_gemini.assert_not_called()

    def test_cache_miss_calls_provider_and_stores_result(self):
        prompt = "Evaluate this rubric submission"
        expected = {"score": 95, "summary": "Excellent work"}

        with patch(
            "app.gemini._generate_with_gemini", return_value=expected
        ) as mock_gemini:
            result = generate_json(prompt, model="flash", use_cache=True)
            self.assertEqual(result, expected)
            self.assertEqual(mock_gemini.call_count, 1)

        # Second invocation hits the cache
        with patch("app.gemini._generate_with_gemini") as mock_gemini_2:
            second = generate_json(prompt, model="flash", use_cache=True)
            self.assertEqual(second, expected)
            mock_gemini_2.assert_not_called()

    def test_ttl_expiration_evicts_old_entries(self):
        prompt = "Transient prompt"
        set_cached_response(prompt, {"ok": True}, model="flash", ttl_seconds=-1)
        self.assertIsNone(get_cached_response(prompt, model="flash"))

    def test_semantic_cache_requires_matching_safe_scope(self):
        prompt = 'Create a Python quiz about list comprehensions and loops.'
        payload = {'questions': [{'question': 'What is a comprehension?'}]}
        set_cached_response(
            prompt, payload, model='flash', semantic_scope='quiz:lists:v1',
        )
        near_duplicate = 'Create a Python quiz about loops and list comprehensions.'
        self.assertEqual(
            get_semantic_cached_response(
                near_duplicate, scope='quiz:lists:v1', model='flash',
            ),
            payload,
        )
        self.assertIsNone(get_semantic_cached_response(
            near_duplicate, scope='quiz:other:v1', model='flash',
        ))


if __name__ == '__main__':
    unittest.main()
