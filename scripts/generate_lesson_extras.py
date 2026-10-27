#!/usr/bin/env python3
"""Generate beginner explanations and self-check answers for every lesson.

The bundled curriculum is the source of truth for the course.  This script adds
a plain-language layer on top of it:

* an ``intro`` that says what the lesson is about in everyday words,
* a ``plain`` explanation and a tiny ``example`` for each core concept,
* a direct ``answer`` for every self-check question.

Results are written to ``app/data/lesson_extras.json`` so the lesson page can
render them without calling an AI service at request time.  The script is
resumable: lessons that already have a complete entry are skipped.

Usage:
    python scripts/generate_lesson_extras.py --limit 5
    python scripts/generate_lesson_extras.py --lesson 1.01
    python scripts/generate_lesson_extras.py            # all remaining lessons

The public generation endpoint allows one reply every 30 seconds per IP, so a
full run takes roughly 100 minutes.  Run it in the background when needed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CURRICULUM = ROOT / "app" / "data" / "dynamoai_curriculum.json"
OUTPUT = ROOT / "app" / "data" / "lesson_extras.json"
ENDPOINT = os.environ.get(
    "LESSON_EXTRAS_ENDPOINT", "https://text.pollinations.ai/openai"
)
DEFAULT_DELAY = 31
MAX_ATTEMPTS = 6


SYSTEM_PROMPT = (
    "You are a patient senior engineer who teaches complete beginners. "
    "You explain one idea at a time in short, plain sentences. You define "
    "jargon the first time you use it and never invent facts. "
    "Return valid JSON only, with no markdown fences or commentary."
)


def load_curriculum():
    """Load lessons with the same structured concepts the web app renders."""
    sys.path.insert(0, str(ROOT))
    from app.curriculum import all_lessons

    return {"lessons": all_lessons()}


def load_output():
    if not OUTPUT.exists():
        return {}
    try:
        with OUTPUT.open(encoding="utf-8") as source:
            data = json.load(source)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_output(data):
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8") as target:
        json.dump(data, target, indent=1, ensure_ascii=False, sort_keys=True)
        target.write("\n")
    temporary.replace(OUTPUT)


def compact(text, limit):
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def concept_text(lesson):
    concepts = lesson.get("concepts")
    if concepts:
        return "\n".join(
            f"- {item['title']}: {' '.join(item.get('paragraphs') or [])}"
            for item in concepts
        )
    blocks = lesson.get("core_concepts") or []
    return "\n".join(
        f"- {item.get('title', 'Concept')}: {item.get('content', '')}"
        for item in blocks
        if isinstance(item, dict)
    )


def build_prompt(lesson):
    key_terms = lesson.get("key_terms") or []
    terms = "\n".join(
        f"- {item.get('term')}: {item.get('definition')}"
        if isinstance(item, dict)
        else f"- {item}"
        for item in key_terms
    )
    questions = lesson.get("questions") or []
    numbered = "\n".join(
        f"{index + 1}. {question}" for index, question in enumerate(questions)
    )
    concepts = lesson.get("concepts") or [
        {
            "title": item.get("title") or "Concept",
            "paragraphs": [item.get("content", "")],
        }
        for item in (lesson.get("core_concepts") or [])
        if isinstance(item, dict)
    ]
    concept_blocks = []
    for index, concept in enumerate(concepts, start=1):
        body = compact(" ".join(concept.get("paragraphs") or []), 1400)
        concept_blocks.append(
            f"{index}. TITLE: {concept.get('title') or 'Concept'}\n"
            f"   SOURCE: {body}"
        )
    material = "\n\n".join(concept_blocks)
    return f"""LESSON
Title: {lesson.get('title')}
Summary: {lesson.get('subtitle')}
Why it matters: {compact(' '.join(lesson.get('why_it_matters') or []), 700)}
Key terms:
{compact(terms, 700)}

CORE CONCEPTS AND THEIR SOURCE TEXT
{material}

SELF-CHECK QUESTIONS
{numbered}

TASK
Write for someone who has never programmed before. Return one JSON object:

{{
  "intro": "2-3 short sentences: what this lesson is about and why a beginner should care. No jargon.",
  "concepts": [
    {{"title": "exact title copied from the source material", "plain": "2-3 short sentences that explain THIS concept's source text in everyday words", "example": "one concrete, tiny example (a sentence, not a program)"}}
  ],
  "answers": ["direct answer to question 1", "direct answer to question 2", "... one answer per question, in order"]
}}

Rules:
- There are exactly {len(concepts)} concepts. Return one entry per concept, in the same order, with the title copied exactly.
- Each "plain" explanation must restate the idea in that concept's SOURCE, not a nearby or general idea.
- Each "example" must be concrete and under 25 words.
- Answer each question with 1-3 sentences. The answer must be consistent with the source text above and must not contradict it. Do not start with "The lesson says".
- When a question asks which part of a traceback holds the cause, which data structure to use, or what a call does, state the precise answer from the source.
- Exactly {len(questions)} answers, in the same order as the questions.
"""


def build_critique_prompt(lesson, draft):
    questions = lesson.get("questions") or []
    numbered = "\n".join(
        f"{index + 1}. {question}" for index, question in enumerate(questions)
    )
    concepts = lesson.get("concepts") or []
    material = "\n\n".join(
        f"- {concept.get('title')}: {' '.join(concept.get('paragraphs') or [])}"
        for concept in concepts
    )
    return f"""You are checking a beginner study guide for factual errors.

LESSON: {lesson.get('title')}
SOURCE MATERIAL:
{compact(material, 5000)}

QUESTIONS:
{numbered}

DRAFT GUIDE:
{json.dumps(draft, ensure_ascii=False)}

TASK
Check every entry against the source material. Rewrite any answer or explanation that is wrong, contradicts the source, or explains a different idea. Keep correct entries unchanged. Improve clarity with shorter sentences. Return the complete corrected JSON object with the same keys: intro, concepts, answers. No commentary.
"""


def call_endpoint(prompt):
    body = json.dumps(
        {
            "model": os.environ.get("LESSON_EXTRAS_MODEL", "openai"),
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.25,
            "max_tokens": 6000,
        }
    ).encode("utf-8")
    request = Request(
        ENDPOINT,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=240) as response:
        payload = json.load(response)
    return payload["choices"][0]["message"]["content"]


def parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("response did not contain a JSON object")
    return json.loads(text[start : end + 1])


def normalise(lesson, payload):
    expected_titles = [
        item.get("title") or "Concept"
        for item in (lesson.get("concepts") or lesson.get("core_concepts") or [])
    ]
    raw_concepts = payload.get("concepts")
    if not isinstance(raw_concepts, list):
        raise ValueError("concepts must be a list")
    concepts = []
    for index, title in enumerate(expected_titles):
        candidate = raw_concepts[index] if index < len(raw_concepts) else {}
        if not isinstance(candidate, dict):
            candidate = {}
        removed = str(candidate.get("plain") or "").strip()
        removed = " ".join(removed.split())
        if len(removed) < 20:
            raise ValueError(f"concept {index + 1} has no usable explanation")
        concepts.append(
            {
                "title": title,
                "plain": removed,
                "example": compact(candidate.get("example"), 240),
            }
        )

    raw_answers = payload.get("answers")
    questions = lesson.get("questions") or []
    if not isinstance(raw_answers, list) or len(raw_answers) != len(questions):
        raise ValueError(
            f"expected {len(questions)} answers, got "
            f"{len(raw_answers) if isinstance(raw_answers, list) else 'none'}"
        )
    answers = []
    for index, answer in enumerate(raw_answers):
        answer = " ".join(str(answer or "").split())
        if len(answer) < 25:
            raise ValueError(f"answer {index + 1} is too short")
        answers.append(answer)

    intro = " ".join(str(payload.get("intro") or "").split())
    if len(intro) < 40:
        raise ValueError("intro is too short")
    return {"intro": intro, "concepts": concepts, "answers": answers}


def is_complete(entry, lesson):
    if not isinstance(entry, dict):
        return False
    questions = lesson.get("questions") or []
    concepts = lesson.get("concepts") or lesson.get("core_concepts") or []
    return (
        isinstance(entry.get("intro"), str)
        and isinstance(entry.get("answers"), list)
        and len(entry["answers"]) == len(questions)
        and isinstance(entry.get("concepts"), list)
        and len(entry["concepts"]) == len(concepts)
    )


def generate(lesson, delay, verify=False):
    prompt = build_prompt(lesson)
    entry = _generate_json(prompt, delay)
    result = normalise(lesson, entry)
    if verify:
        time.sleep(delay)
        critique = build_critique_prompt(lesson, result)
        corrected = _generate_json(critique, delay)
        result = normalise(lesson, corrected)
    return result


def _generate_json(prompt, delay):
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raw = call_endpoint(prompt)
            return parse_json(raw)
        except HTTPError as error:
            body = ""
            try:
                body = error.read().decode("utf-8", "replace")
            except Exception:
                pass
            last_error = f"HTTP {error.code}: {body[:160]}"
            if error.code in (402, 429, 500, 502, 503, 504):
                wait = delay
            else:
                wait = 5
        except (URLError, TimeoutError, OSError) as error:
            last_error = f"network: {error}"
            wait = 10
        except (ValueError, KeyError, TypeError) as error:
            last_error = f"invalid response: {error}"
            wait = 3
        if attempt < MAX_ATTEMPTS:
            print(f"    retry {attempt}/{MAX_ATTEMPTS} in {wait}s ({last_error})")
            time.sleep(wait)
    raise RuntimeError(f"could not generate lesson: {last_error}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lesson", help="generate a single lesson id, e.g. 1.01")
    parser.add_argument("--limit", type=int, default=0, help="stop after N lessons")
    parser.add_argument(
        "--delay", type=int, default=DEFAULT_DELAY,
        help=f"seconds between requests (default {DEFAULT_DELAY})",
    )
    parser.add_argument(
        "--force", action="store_true", help="regenerate lessons that already exist"
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="run a second pass that checks answers against the source",
    )
    args = parser.parse_args()

    data = load_curriculum()
    lessons = data.get("lessons") or []
    extra = load_output()

    if args.lesson:
        lessons = [lesson for lesson in lessons if lesson.get("id") == args.lesson]
        if not lessons:
            raise SystemExit(f"unknown lesson id: {args.lesson}")
    if args.verify and not args.lesson:
        raise SystemExit("--verify requires --lesson (the free endpoint is slow)")

    pending = [
        lesson for lesson in lessons
        if args.force or not is_complete(extra.get(lesson.get("id")), lesson)
    ]
    if args.limit:
        pending = pending[: args.limit]

    total = len(pending)
    print(f"{total} lesson(s) to generate; {len(extra)} already present")
    for index, lesson in enumerate(pending, start=1):
        lesson_id = lesson["id"]
        print(f"[{index}/{total}] {lesson_id} {lesson.get('title')}", flush=True)
        try:
            entry = generate(lesson, args.delay, verify=args.verify)
        except RuntimeError as error:
            print(f"  FAILED: {error}", flush=True)
            continue
        extra[lesson_id] = entry
        save_output(extra)
        print(f"  saved ({len(entry['answers'])} answers)", flush=True)
        if index < total:
            time.sleep(args.delay)
    print(f"done: {len(extra)} lesson entries in {OUTPUT}")


if __name__ == "__main__":
    main()
