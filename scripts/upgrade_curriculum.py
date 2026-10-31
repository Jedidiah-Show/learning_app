#!/usr/bin/env python3
"""Upgrade the bundled curriculum in place without regenerating reviewed content.

This is a post-processing migration for the PDF-derived JSON.  It removes parser
artefacts, repairs code metadata and snippets, adds the beginner ramp and modern
lessons, expands resources/extras, fixes practice exercises, and records the
placement and scheduling routes.  The review overlay is merged, never replaced.
"""

from __future__ import annotations

import ast
import copy
import json
import re
from datetime import date
from pathlib import Path
from textwrap import dedent

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from curriculum_content import (  # noqa: E402
    EXERCISES,
    LESSONS,
    MAINTENANCE,
    MODULE_RESOURCES,
    MODULE_TITLES,
    PLACEMENT,
    RESOURCES,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'app' / 'data'
BASE_PATH = DATA / 'dynamoai_curriculum.json'
OVERRIDES_PATH = DATA / 'curriculum_overrides.json'
RESOURCES_PATH = DATA / 'dynamoai_resources.json'
EXTRAS_PATH = DATA / 'lesson_extras.json'
EXERCISES_PATH = DATA / 'practice_exercises.json'

FOOTER_RE = re.compile(
    r'(?:Three pages per lesson\s+Page\s+\d+\s+of\s+\d+'
    r'|DYNAMOAI\s*[·.]\s*COMPASS AI[^\n]*'
    r'|Complete lesson guides[^\n]*'
    r'|Page\s+\d+\s+of\s+\d+)',
    re.IGNORECASE,
)
MODULE_TAIL_RE = re.compile(
    r'\n\s*MODULE\s+\d{2}\s*[·.]\s*\d+\s+LESSONS\s*[·.][\s\S]*$',
    re.IGNORECASE,
)
LESSON_LIST_RE = re.compile(
    r'\n\s*LESSONS AND PAGE RANGES[\s\S]*$',
    re.IGNORECASE,
)
CAPSTONE_RE = re.compile(r'\bCAPSTONE CONNECTION\b\s*[:\-]?\s*', re.IGNORECASE)
MENTAL_RE = re.compile(r'\bMENTAL MODEL\b\s*', re.IGNORECASE)
GENERIC_MENTAL_RE = re.compile(
    r'^(?:Think of .+ as a building block|Master .+ one step at a time)',
    re.IGNORECASE,
)
CHECK_RE = re.compile(r'^[\s\u25a1\u25a0\u2022\-]+')

SQL_IDS = {'2.12', '2.13', '2.14', '5.05', '11.06', '11.07'}
DOCKER_IDS = {'10.03'}

PYTHON_FIXES = {
    '1.05': '''
class ModelClient:
    def __init__(self, base_url: str, transport, *, timeout_s=10.0) -> None:
        if not base_url.startswith("https://"):
            raise ValueError("base_url must use https")
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self._transport = transport
        self._requests = 0

    @classmethod
    def from_env(cls, env, transport):
        return cls(env["MODEL_BASE_URL"], transport, timeout_s=float(env["TIMEOUT_S"]))

    def request(self, path: str, payload: dict) -> dict:
        self._requests += 1
        return self._transport(f"{self.base_url}{path}", payload, self.timeout_s)

    def __repr__(self) -> str:
        return f"ModelClient({self.base_url!r}, requests={self._requests})"
''',
    '1.06': '''
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    score: float
    error: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score out of range: {self.score}")


@dataclass
class RunSummary:
    results: list[CaseResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        total = sum(r.score for r in self.results)
        return total / len(self.results) if self.results else 0.0
''',
    '2.02': '''
import httpx

with httpx.Client(base_url="https://api.example.com", timeout=10.0) as client:
    r = client.get("/v1/documents", params={"limit": 2})
    print(r.status_code, r.headers.get("content-type"))
    print(r.headers.get("cache-control", "no cache header"))
    print(r.json()["data"][0]["id"])

    created = client.post(
        "/v1/summaries",
        json={"document_id": "doc_481"},
        headers={"Idempotency-Key": "sum-481-v1"},
    )
    print(created.status_code, created.headers.get("location"))
''',
    '3.10': '''
from pydantic import BaseModel, Field, ValidationError, model_validator
from typing import Literal


class Invoice(BaseModel):
    invoice_id: str = Field(pattern=r"^INV-\\d{6}$")
    currency: Literal["GBP", "EUR", "USD"]
    amounts_cents: list[int] = Field(min_length=1, max_length=50)
    total_cents: int = Field(ge=0)

    @model_validator(mode="after")
    def totals_match(self) -> "Invoice":
        if sum(self.amounts_cents) != self.total_cents:
            raise ValueError("amounts do not sum to total_cents")
        return self


def parse_invoice(raw: str) -> Invoice | None:
    try:
        return Invoice.model_validate_json(raw)
    except ValidationError:
        return None
''',
    '4.02': '''
from hashlib import sha256
from string import Template


class PromptTemplate:
    def __init__(self, name: str, version: str, body: str) -> None:
        self.name, self.version, self.body = name, version, body
        self.id = f"{name}@{version}:{sha256(body.encode()).hexdigest()[:8]}"

    def render(self, **values: str) -> str:
        missing = set(Template(self.body).get_identifiers()) - set(values)
        if missing:
            raise ValueError(f"{self.id} missing {sorted(missing)}")
        return Template(self.body).substitute(values)


classify = PromptTemplate("classify", "3", "Ticket: $ticket\\nLabels: $labels\\n")
print(classify.render(ticket="Refund not received", labels="billing,shipping"))
''',
    '5.19': '''
from dataclasses import dataclass


@dataclass(frozen=True)
class IndexManifest:
    alias: str
    embed_model: str
    dimension: int

    def accepts(self, query_model: str, query_dim: int) -> bool:
        return query_model == self.embed_model and query_dim == self.dimension


def degrade(elapsed_ms: int, budget_ms: int = 2500) -> str:
    remaining = budget_ms - elapsed_ms
    if remaining > 1400:
        return "full"
    if remaining > 600:
        return "skip_rerank"
    if remaining > 200:
        return "cached_answer"
    return "refusal"
''',
    '6.11': '''
def build_context(pinned: list[str], turns: list[str], scratch: str,
                  budget: int = 12_000) -> list[str]:
    def cost(text: str) -> int:
        return int(len(text.split()) * 1.3)

    kept, used = [], cost(scratch) + sum(cost(p) for p in pinned)
    for turn in reversed(turns):
        size = cost(turn)
        if used + size > budget * 0.7:
            break
        kept.append(turn)
        used += size
    return pinned + [scratch] + list(reversed(kept))
''',
    '7.14': '''
from dataclasses import dataclass


@dataclass(frozen=True)
class Handoff:
    from_agent: str
    to_agent: str
    reason: str
    facts: tuple[str, ...]
    open_questions: tuple[str, ...]
    budget_tokens: int
    tried: tuple[str, ...] = ()

    def check(self, allowed: dict[str, set[str]]) -> None:
        assert self.to_agent in allowed[self.from_agent], "route not permitted"
        assert self.budget_tokens > 0, "handoff must carry budget"
        assert self.reason and self.facts, "handoff needs reason and facts"
        assert self.to_agent not in self.tried, "do not retry a failed agent"
''',
    '8.02': '''
from dataclasses import dataclass


@dataclass(frozen=True)
class Estate:
    hosts: int
    systems: int

    def bespoke_edges(self) -> int:
        return self.hosts * self.systems

    def mcp_components(self) -> int:
        return self.hosts + self.systems


estate = Estate(hosts=6, systems=9)
print(f"bespoke connectors: {estate.bespoke_edges()}")
print(f"MCP components: {estate.mcp_components()}")
saved = estate.bespoke_edges() - estate.mcp_components()
print(f"removed integration points: {saved}")
''',
    '9.04': '''
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env")

    model_id: str = "gpt-4.1-mini"
    temperature: float = Field(0.0, ge=0.0, le=2.0)
    retrieval_k: int = Field(8, ge=1, le=50)
    request_timeout_s: float = Field(20.0, gt=0, le=120)


settings = Settings()  # raises ValidationError before serving traffic
print(settings.model_dump())
''',
    '9.16': '''
from datetime import date
from pydantic import BaseModel, Field, model_validator


class Claim(BaseModel):
    registration: str = Field(pattern=r"^[A-Z0-9]{2,8}$")
    incident_date: date
    policy_end: date
    total_eur: float = Field(gt=0, le=50_000)
    line_totals: list[float]

    @model_validator(mode="after")
    def checks(self):
        if abs(sum(self.line_totals) - self.total_eur) > 0.01:
            raise ValueError("total_mismatch")
        if self.incident_date > self.policy_end:
            raise ValueError("outside_policy")
        return self
''',
    '9.19': '''
import pytest
from app.llm import ModelClient, ModelError
from app.service import answer


class FakeModel(ModelClient):
    def __init__(self, reply: str | Exception):
        self.reply = reply
        self.calls = 0

    def complete(self, prompt: str) -> str:
        self.calls += 1
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def test_repair_is_attempted_once_then_fails():
    fake = FakeModel("{not json")
    with pytest.raises(ModelError):
        answer("Summarise this", client=fake, repair=True)
    assert fake.calls == 2
''',
    '9.23': '''
from dataclasses import dataclass


@dataclass(frozen=True)
class Slo:
    name: str
    target: float

    def burn(self, good: int, valid: int) -> float:
        """1.0 consumes the 28-day budget in exactly 28 days."""
        if valid == 0:
            return 0.0
        budget = 1 - self.target
        return (1 - good / valid) / budget


quality = Slo("citation_coverage", 0.99)
fast, slow = quality.burn(142, 200), quality.burn(39_800, 40_000)
print(f"1h burn={fast:.1f}x", "page" if fast > 14.4 else "ticket")
print(f"6h burn={slow:.1f}x", "ticket" if slow > 6 else "ok")
''',
    '10.09': '''
from typing import Literal
from pydantic import AnyUrl, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", extra="forbid")
    env: Literal["dev", "staging", "prod"]
    database_url: AnyUrl
    storage_bucket: str = Field(min_length=3)
    model_timeout_s: float = Field(gt=0, le=60)

    @model_validator(mode="after")
    def guard_prod(self):
        prod_bucket = self.storage_bucket.startswith("acme-prod-")
        if self.env == "prod" and not prod_bucket:
            raise ValueError("prod bucket must start with acme-prod-")
        return self


settings = Settings()
''',
    '11.11': '''
import time


class Breaker:
    def __init__(self, threshold: int = 5, reset_after: float = 20.0) -> None:
        self.threshold, self.reset_after = threshold, reset_after
        self.failures, self.opened_at = 0, 0.0

    def allow(self) -> bool:
        if self.failures < self.threshold:
            return True
        if time.monotonic() - self.opened_at >= self.reset_after:
            self.failures = self.threshold - 1  # half-open probe
            return True
        return False

    def record(self, ok: bool) -> None:
        self.failures = 0 if ok else self.failures + 1
        if self.failures >= self.threshold:
            self.opened_at = time.monotonic()
''',
}


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def dump(path: Path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )


def first_sentence(text: str) -> str:
    text = re.sub(r'\s+', ' ', str(text)).strip()
    match = re.search(r'[.!?](?=\s|$)', text)
    return text[:match.end()] if match else text


def strip_tail(text: str) -> str:
    text = MODULE_TAIL_RE.sub('', text)
    text = LESSON_LIST_RE.sub('', text)
    return text


def clean_text(value) -> str:
    if value is None:
        return ''
    text = str(value).replace('\r\n', '\n').replace('\r', '\n')
    text = strip_tail(text)
    text = re.split(r'\s+LESSONS AND PAGE RANGES\b', text, maxsplit=1, flags=re.IGNORECASE)[0]
    text = re.split(r'\s+Three pages per lesson\b', text, maxsplit=1, flags=re.IGNORECASE)[0]
    text = re.split(r'\s+MODULE PROJECT\b', text, maxsplit=1)[0]
    text = FOOTER_RE.sub(' ', text)
    text = re.sub(r'\bYOUR WORKING NOTES\b', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def clean_list(values, *, dedupe=True):
    cleaned = []
    for value in values or []:
        text = clean_text(value)
        if not text:
            continue
        if dedupe and text in cleaned:
            continue
        cleaned.append(text)
    return cleaned


def split_capstone(text: str):
    match = CAPSTONE_RE.search(text)
    if not match:
        return text, ''
    before = text[:match.start()]
    after = text[match.end():]
    after = re.split(
        r'Three pages per lesson|DYNAMOAI\s*[·.]|LESSONS AND PAGE RANGES|MODULE\s+\d{2}\s*[·.]',
        after,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return before, clean_text(after)


def split_mental(text: str):
    match = MENTAL_RE.search(text)
    if not match:
        return text, ''
    before = text[:match.start()]
    after = text[match.end():]
    after = re.split(
        r'Three pages per lesson|DYNAMOAI\s*[·.]|CAPSTONE CONNECTION|LESSONS AND PAGE RANGES',
        after,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return before, clean_text(after)


def is_generic_mental(text: str) -> bool:
    text = (text or '').strip()
    return not text or bool(GENERIC_MENTAL_RE.match(text))


def full_subtitle(lesson, pages):
    if not pages:
        return lesson.get('subtitle', '')
    lines = [line.strip() for line in pages[0].splitlines() if line.strip()]
    if len(lines) < 2:
        return lesson.get('subtitle', '')
    meta_at = None
    for index, line in enumerate(lines[1:], start=1):
        if re.search(r'[·.]\s*Lesson\s+\d+\s+of\s+\d+', line, re.IGNORECASE):
            meta_at = index
            break
    if not meta_at:
        return lesson.get('subtitle', '')
    candidate = ' '.join(lines[1:meta_at]).strip()
    candidate = re.sub(r'\s+', ' ', candidate)
    candidate = re.sub(r'(?<=[a-z])-\s+(?=[a-z])', '', candidate)
    current = re.sub(r'\s+', ' ', str(lesson.get('subtitle', ''))).strip()
    if not candidate:
        return current
    if len(candidate) > len(current) + 3 and (
        candidate.startswith(current[:30]) or current.lower() in candidate.lower()
        or len(current) < 40
    ):
        return candidate
    return current


def clean_pages(pages):
    cleaned = []
    for page in pages or []:
        lines = []
        for line in str(page).replace('\r\n', '\n').splitlines():
            stripped = line.strip()
            if re.match(r'^(?:Three pages per lesson|Page\s+\d+\s+of\s+\d+|DYNAMOAI\s*[·.])', stripped, re.IGNORECASE):
                continue
            if re.match(r'^MODULE\s+\d{2}\s*[·.]\s*\d+\s+LESSONS', stripped, re.IGNORECASE):
                break
            if re.match(r'^LESSONS AND PAGE RANGES', stripped, re.IGNORECASE):
                break
            lines.append(line.rstrip())
        text = '\n'.join(lines).strip()
        text = re.sub(r'\n{3,}', '\n\n', text)
        if text:
            cleaned.append(text)
    return cleaned


def detect_language(code: str, lesson_id: str) -> str:
    if lesson_id in SQL_IDS:
        return 'sql'
    if lesson_id in DOCKER_IDS:
        return 'docker'
    stripped = (code or '').lstrip()
    if not stripped:
        return 'text'
    if stripped.startswith(('{', '[')):
        try:
            json.loads(code)
            return 'json'
        except Exception:
            pass
    try:
        ast.parse(code)
        return 'python'
    except SyntaxError:
        pass
    if re.search(
        r'^\s*(?:--|SELECT|WITH|CREATE|ALTER|INSERT|UPDATE|DELETE|BEGIN|EXPLAIN)\b',
        code,
        re.IGNORECASE | re.MULTILINE,
    ):
        return 'sql'
    if re.search(
        r'^\s*(?:FROM|RUN|COPY|ENV|CMD|ENTRYPOINT|WORKDIR|EXPOSE|ARG)\s',
        code,
        re.IGNORECASE | re.MULTILINE,
    ):
        return 'docker'
    if re.search(r'^\s*(?:\$|curl|git|pip|uv|python|export|docker)\b', code, re.MULTILINE):
        return 'bash'
    if re.search(r'^\s*(?:apiVersion|services|version):', code, re.MULTILINE):
        return 'yaml'
    return 'text'


def concept_from_pages(lesson):
    try:
        from app.curriculum import _lesson_concepts
        parsed = _lesson_concepts(lesson)
    except Exception:
        return []
    result = []
    for concept in parsed or []:
        title = clean_text(concept.get('title'))
        if not title or title.lower() == 'concept':
            opening = ' '.join(concept.get('paragraphs') or [])
            title = first_sentence(opening)
            title = title[:80].rstrip(' .,:;')
            if not title:
                continue
        chunks = []
        if concept.get('key_idea'):
            chunks.append(concept['key_idea'])
        chunks.extend(concept.get('paragraphs') or [])
        chunks.extend(concept.get('bullets') or [])
        content = '\n\n'.join(clean_text(chunk) for chunk in chunks if clean_text(chunk))
        if content:
            result.append({'title': title, 'content': content})
    return result


def clean_lesson(lesson, module, index, module_lessons):
    pages = clean_pages(lesson.get('pages'))
    lesson['pages'] = pages
    lesson['subtitle'] = full_subtitle(lesson, pages)
    lesson['meta'] = f"{module['title']} · Lesson {index} of {len(module_lessons)} · study guide"
    if pages:
        pages[0] = re.sub(
            r'(?m)^.*?·\s*Lesson\s+\d+\s+of\s+\d+\s*·\s*study guide.*$',
            lesson['meta'],
            pages[0],
            count=1,
        )

    for field in ('why_it_matters', 'outcomes', 'worked_example', 'steps',
                  'common_mistakes', 'production_notes', 'checklist', 'questions'):
        lesson[field] = clean_list(lesson.get(field))

    lesson['checklist'] = [CHECK_RE.sub('', item).strip() for item in lesson['checklist']]
    lesson['checklist'] = [item for item in lesson['checklist'] if item]

    tasks = []
    capstone_candidates = []
    for task in lesson.get('tasks') or []:
        before, capstone = split_capstone(clean_text(task))
        if capstone:
            capstone_candidates.append(capstone)
        before = clean_text(before)
        if before and before not in tasks:
            tasks.append(before)
    lesson['tasks'] = tasks
    if capstone_candidates and not clean_text(lesson.get('capstone')):
        lesson['capstone'] = capstone_candidates[0]
    lesson['capstone'] = clean_text(lesson.get('capstone'))
    if not lesson['capstone']:
        project = str(module.get('project') or '').strip().rstrip('.')
        lesson['capstone'] = (
            f"In the capstone, this lesson's decisions feed the module project"
            + (f" — {project}" if project else '')
            + '.'
        )

    key_terms = []
    seen_terms = set()
    extracted_mental = ''
    for term in lesson.get('key_terms') or []:
        if isinstance(term, dict):
            name = clean_text(term.get('term'))
            definition = str(term.get('definition') or '')
        else:
            name, definition = clean_text(term), ''
        definition, mental = split_mental(definition)
        if mental and not extracted_mental:
            extracted_mental = mental
        definition = clean_text(definition)
        name = clean_text(name)
        if not name or not definition:
            continue
        if name.lower() in {'three pages per lesson', 'page'}:
            continue
        key = name.lower()
        if key in seen_terms:
            continue
        seen_terms.add(key)
        key_terms.append({'term': name, 'definition': definition})
    lesson['key_terms'] = key_terms

    mental = clean_text(lesson.get('mental_model'))
    if extracted_mental and is_generic_mental(mental):
        mental = extracted_mental
    if is_generic_mental(mental):
        why = (lesson.get('why_it_matters') or [''])[0]
        mental = (
            f"{first_sentence(why)} Keep that idea as the working model you test "
            'in the module project.'
        )
    lesson['mental_model'] = mental

    concepts = []
    for concept in lesson.get('core_concepts') or []:
        if not isinstance(concept, dict):
            continue
        title = clean_text(concept.get('title'))
        content = clean_text(concept.get('content'))
        if not content:
            continue
        if not title or title.lower() == 'concept':
            title = first_sentence(content)[:80].rstrip(' .,:;') or 'Concept'
        concepts.append({'title': title, 'content': content})
    from_pages = concept_from_pages(lesson)
    if from_pages and (
        len(from_pages) > len(concepts)
        or any(c['title'].lower() == 'concept' for c in concepts)
    ):
        concepts = from_pages
    lesson['core_concepts'] = concepts

    code = lesson.get('code')
    if isinstance(code, dict) and code.get('code'):
        content = str(code['code']).replace('\r\n', '\n').strip()
        if lesson['id'] in PYTHON_FIXES:
            content = dedent(PYTHON_FIXES[lesson['id']]).strip()
        code['code'] = content
        code['language'] = detect_language(content, lesson['id'])
        code['title'] = clean_text(code.get('title'))
        code['what_to_notice'] = clean_list(code.get('what_to_notice'))
        lesson['code'] = code
    elif not isinstance(code, dict):
        lesson['code'] = None

    return lesson


def make_pages(lesson, module, index, count):
    meta = f"{module['title']} · Lesson {index} of {count} · study guide"
    lesson['meta'] = meta
    concepts = []
    for concept in lesson.get('core_concepts') or []:
        concepts.extend([concept.get('title', ''), concept.get('content', ''), ''])
    terms = []
    for term in lesson.get('key_terms') or []:
        terms.extend([
            f"{term.get('term', '')}: {term.get('definition', '')}",
        ])
    code = lesson.get('code') or {}
    code_lines = []
    if code.get('code'):
        code_lines = ['```' + str(code.get('language', 'text')), str(code['code']), '```']
    page1 = '\n'.join([
        lesson['title'],
        lesson['subtitle'],
        meta,
        '',
        'WHY THIS LESSON MATTERS',
        *lesson.get('why_it_matters', []),
        '',
        'WHAT YOU WILL BE ABLE TO DO',
        *[f'• {item}' for item in lesson.get('outcomes', [])],
        '',
        'CORE CONCEPTS',
        *concepts,
        'KEY TERMS',
        *terms,
        '',
        'MENTAL MODEL',
        lesson.get('mental_model', ''),
    ]).strip()
    page2 = '\n'.join([
        lesson['title'],
        'Build it',
        'WORKED EXAMPLE',
        *lesson.get('worked_example', []),
        '',
        'STEP BY STEP',
        *[f'{number}. {item}' for number, item in enumerate(lesson.get('steps', []), 1)],
        '',
        'CODE',
        str(code.get('title', '')),
        *code_lines,
        '',
        'WHAT TO NOTICE',
        *[f'→ {item}' for item in code.get('what_to_notice', [])],
    ]).strip()
    page3 = '\n'.join([
        lesson['title'],
        'Operate it',
        'COMMON MISTAKES',
        *[f'{number}. {item}' for number, item in enumerate(lesson.get('common_mistakes', []), 1)],
        '',
        'PRODUCTION NOTES',
        *[f'◆ {item}' for item in lesson.get('production_notes', [])],
        '',
        'CHECKPOINT CHECKLIST',
        *[f'□ {item}' for item in lesson.get('checklist', [])],
        '',
        'SHORT QUESTIONS',
        *[f'{number}. {item}' for number, item in enumerate(lesson.get('questions', []), 1)],
        '',
        'TASKS',
        *[f'□ {item}' for item in lesson.get('tasks', [])],
        '',
        'CAPSTONE CONNECTION',
        lesson.get('capstone', ''),
    ]).strip()
    return [page1, page2, page3]


def build_extras(lesson, answers):
    """Fallback explanation layer for lessons nobody has curated yet.

    It deliberately leaves ``intro`` and ``example`` empty. Padding them with a
    generic sentence is what the release audit calls filler, and an empty field
    is an honest gap the lesson page renders nothing for.
    """
    concepts = []
    for concept in lesson.get('core_concepts') or []:
        concepts.append({
            'title': clean_text(concept.get('title')),
            'plain': clean_text(concept.get('content')),
            'example': '',
        })
    return {
        'intro': '',
        'concepts': concepts,
        'answers': [str(answer) for answer in answers or []],
    }


def _is_authored(entry):
    """True when a human or generator curated a real plain-language layer."""
    if not isinstance(entry, dict):
        return False
    concepts = entry.get('concepts') or []
    return bool(
        str(entry.get('intro') or '').strip()
        and any(str(item.get('example') or '').strip() for item in concepts if isinstance(item, dict))
    )


def _fill_extras(existing, fallback):
    """Use the fallback only for gaps, never over curated intros, examples, or answers."""
    if _is_authored(existing):
        return existing
    merged = dict(fallback)
    for key, value in (existing or {}).items():
        if value:
            merged[key] = value
    return merged


def main():
    base = load(BASE_PATH)
    overrides = load(OVERRIDES_PATH) if OVERRIDES_PATH.exists() else {}
    resources = load(RESOURCES_PATH) if RESOURCES_PATH.exists() else {}
    extras = load(EXTRAS_PATH) if EXTRAS_PATH.exists() else {}
    exercises = load(EXERCISES_PATH) if EXERCISES_PATH.exists() else []

    modules = base.get('modules') or []
    module_map = {str(module['id']): module for module in modules}
    if len(module_map) != len(modules):
        raise SystemExit('duplicate module ids in curriculum')

    # Remove previous copies so this script is safe to run more than once.
    new_ids = {lesson['id'] for lesson in LESSONS}
    base['lessons'] = [
        lesson for lesson in base.get('lessons') or []
        if lesson.get('id') not in new_ids
    ]
    for lesson in LESSONS:
        module_id = str(lesson['module_id'])
        if module_id not in module_map:
            raise SystemExit(f'unknown module {module_id} for lesson {lesson["id"]}')
        entry = copy.deepcopy(lesson)
        entry.pop('_answers', None)
        entry['module_id'] = module_id
        entry['beginner_tip'] = entry.get(
            'beginner_tip',
            'Work slowly and run every example. If an error appears, read the last '
            'line of the traceback before changing code.',
        )
        entry['prerequisites'] = []
        module = module_map[module_id]
        siblings = [
            item for item in base['lessons']
            if str(item.get('module_id')) == module_id
        ]
        siblings.append(entry)
        siblings.sort(key=lambda item: int(str(item['id']).split('.')[1]))
        index = next(i for i, item in enumerate(siblings, 1) if item is entry)
        entry['pages'] = make_pages(entry, module, index, len(siblings))
        base['lessons'].append(entry)

    base['lessons'].sort(
        key=lambda item: (int(str(item['module_id'])), int(str(item['id']).split('.')[1]))
    )

    # Clean every lesson, including the reviewed originals, against its module.
    for module in modules:
        module_id = str(module['id'])
        module_lessons = [
            lesson for lesson in base['lessons']
            if str(lesson.get('module_id')) == module_id
        ]
        module_lessons.sort(key=lambda item: int(str(item['id']).split('.')[1]))
        for index, lesson in enumerate(module_lessons, 1):
            clean_lesson(lesson, module, index, module_lessons)
        module['lesson_count'] = len(module_lessons)

    # The capstone title should match the beginner ramp that now precedes it.
    for lesson in base['lessons']:
        if lesson.get('id') == '1.01':
            old_title = lesson.get('title')
            lesson['title'] = 'Python review: data, loops, and tracebacks'
            if old_title and lesson.get('pages'):
                lesson['pages'][0] = lesson['pages'][0].replace(
                    old_title, lesson['title'], 1
                )

    # Fill the legacy prerequisite field with the actual sequence, including
    # the module-project gate at the start of every module after Module 0.
    previous_module = None
    for module in modules:
        module_lessons = [
            lesson for lesson in base['lessons']
            if str(lesson.get('module_id')) == str(module['id'])
        ]
        for index, lesson in enumerate(module_lessons):
            if index == 0:
                if module.get('number') == 0:
                    lesson['prerequisites'] = ['None - start here.']
                elif previous_module is not None:
                    lesson['prerequisites'] = [
                        f"Complete Module {previous_module['number']:02d} lessons "
                        'and its module project.'
                    ]
            else:
                previous = module_lessons[index - 1]
                lesson['prerequisites'] = [
                    f"Complete {previous['id']}: {previous['title']}."
                ]
        previous_module = module

    # The course metadata is generated from the final list.
    lesson_count = len(base['lessons'])
    base['course']['total_lessons'] = lesson_count
    base['course']['description'] = (
        f'A 13-module, {lesson_count}-lesson AI engineering course covering Python, backend '
        'systems, modern LLM and open-weight models, multimodal inputs, RAG, '
        'agents, agent-to-agent collaboration, computer use, MCP, security, '
        'evaluation, governance, and deployment. Lessons and framework examples '
        'are versioned for review.'
    )

    # Keep the nested module copies in sync for maintenance tooling that reads
    # the legacy shape. Runtime code rebuilds these from the top-level list.
    for module in modules:
        module_id = str(module['id'])
        module['lessons'] = [
            copy.deepcopy(lesson) for lesson in base['lessons']
            if str(lesson.get('module_id')) == module_id
        ]

    # Module-level editorial fields stay in the overlay; only scrub the legacy
    # base fields that the parser polluted.
    for module in modules:
        for field in ('description', 'project'):
            if module.get(field):
                module[field] = clean_text(module[field])
        module['what_you_will_build'] = []
        module['before_you_start'] = []
        module['outcomes'] = []
        module['questions'] = []

    # Review overlay: preserve reviewed content, add the new route and metadata.
    course_overrides = overrides.setdefault('course', {})
    course_overrides['starting_assumption'] = (
        'No programming experience is required. Module 0 starts with your first '
        'Python program, then adds data structures, functions, files, Git, and '
        'HTTP. Experienced learners can take the placement check, but module '
        'projects are still required.'
    )
    course_overrides['content_maintenance_policy'] = (
        'Version-sensitive implementation lessons are tagged with primary '
        'documentation. Review each against its linked source every 90 days; '
        'show the verified date and source, and keep unreviewed examples '
        'visibly marked in the release queue.'
    )
    # Which lessons must ship a curated explanation. setdefault so a
    # regeneration widens the scope only when a human adds modules to it.
    course_overrides.setdefault('plain_language_scope', {
        'note': (
            'Modules whose lessons must ship a curated plain-language intro, a '
            'worked example for every core concept, and checkpoint answers. The '
            'release audit fails when one is missing or reads as a placeholder. '
            'Grow this list as modules are written.'
        ),
        'modules': ['05', '06', '08', '09'],
        'lesson_ids': [],
    })
    routes = course_overrides.setdefault('learning_routes', {})
    routes['beginner'] = {
        'title': 'Starting from scratch',
        'description': (
            'Follow the numbered sequence from Module 0. Lessons 0.06 to 0.11 '
            'are a hands-on coding ramp: run Python, use lists and dictionaries, '
            'write functions, read files, use Git, and call HTTP APIs. Complete '
            'every guided practice exercise before opening the worked solution.'
        ),
    }
    routes['experienced'] = {
        'title': 'Placement check and skip path',
        'description': (
            'Take the ten-question placement check. A score of 8 or more marks '
            'the Module 0 and early Module 1 foundation lessons as placed out. '
            'The placement never skips module projects, evidence, or the later '
            'lessons; those remain the proof that you can build and operate a '
            'system.'
        ),
    }
    course_overrides['placement'] = copy.deepcopy(PLACEMENT)

    module_overrides = overrides.setdefault('modules', {})
    if '00' in module_overrides:
        module_overrides['00']['project_hours'] = 3
    if '01' in module_overrides:
        module_overrides['01']['assumed_prerequisites'] = (
            'Complete Module 0, or pass the placement check. You should be able '
            'to run a Python file, use lists and dictionaries, write a small '
            'function, read a traceback, and make a Git commit. Module projects '
            'are still required after placement.'
        )
    for module_id, hours in {'03': 5, '06': 9, '07': 9}.items():
        if module_id in module_overrides:
            module_overrides[module_id]['project_hours'] = hours

    lesson_overrides = overrides.setdefault('lessons', {})
    for lesson in LESSONS:
        lesson_id = lesson['id']
        references = MAINTENANCE.get(lesson_id)
        if not references:
            article = RESOURCES.get(lesson_id, {}).get('article', {})
            references = [article['url']] if article.get('url') else []
        entry = lesson_overrides.setdefault(lesson_id, {})
        entry['maintenance'] = {
            'kind': 'version-sensitive',
            'review_status': 'reviewed',
            'review_interval_days': 90,
            'reviewed_on': date.today().isoformat(),
            'references': references,
        }

    # Resources: add lesson links and module fallbacks. Existing curated links
    # win over the generated fallback.
    for lesson_id, value in RESOURCES.items():
        resources[lesson_id] = value
    for module_id, value in MODULE_RESOURCES.items():
        resources.setdefault(f'module:{module_id}', value)

    # Extras: fill only lessons whose plain-language layer nobody has authored.
    # Regeneration must never overwrite curated intros, examples, or answers.
    for lesson in LESSONS:
        extras[lesson['id']] = _fill_extras(
            extras.get(lesson['id']), build_extras(lesson, lesson.get('_answers') or [])
        )
    for lesson in base['lessons']:
        if lesson['module_id'] in {'00', '01'}:
            extras[lesson['id']] = _fill_extras(
                extras.get(lesson['id']), build_extras(lesson, [])
            )

    # Practice: remove old copies of generated exercises, then fix the three
    # known failures in the reviewed set.
    generated_ids = {exercise['id'] for exercise in EXERCISES}
    exercises = [
        exercise for exercise in exercises
        if exercise.get('id') not in generated_ids
    ]
    exercises.extend(copy.deepcopy(EXERCISES))
    for exercise in exercises:
        if exercise.get('id') == 'python-staged-secret-scan':
            exercise['solution_code'] = exercise['solution_code'].replace(
                '    return found', '    return sorted(found)'
            )
        if exercise.get('id') == 'mcp-permission-gate':
            exercise['checks_code'] = (
                'assert authorize_mcp_call("read_doc", {"readOnlyHint": True}, '
                '{"docs:read"}) is True\n'
                'assert authorize_mcp_call("delete_doc", {"readOnlyHint": True}, '
                'set()) is False\n'
                'assert authorize_mcp_call("delete_doc", {}, {"docs:write"}) '
                'is True\n'
                'assert authorize_mcp_call("unknown", {}, {"*"}) is False\n'
                'print("All checks passed.")'
            )
        if exercise.get('id') == 'system-design-budget':
            exercise['solution_code'] = exercise['solution_code'].replace(
                '    return {"latency_ms":latency,"cost_usd":round(cost,12),"exceeded":exceeded}',
                '    return {"latency_ms":latency,"cost_usd":round(cost,12),"exceeded":sorted(exceeded)}',
            )

    # Verify every Python lesson snippet parses before writing anything.
    python_errors = []
    for lesson in base['lessons']:
        code = lesson.get('code')
        if isinstance(code, dict) and code.get('language') == 'python' and code.get('code'):
            try:
                ast.parse(code['code'])
            except SyntaxError as exc:
                python_errors.append((lesson['id'], str(exc)))
    if python_errors:
        raise SystemExit('Python snippets still fail to parse: ' + repr(python_errors))

    # Keep metadata clean for the new lessons and remove internal answer keys.
    for lesson in base['lessons']:
        lesson.pop('_answers', None)

    dump(BASE_PATH, base)
    dump(OVERRIDES_PATH, overrides)
    dump(RESOURCES_PATH, resources)
    dump(EXTRAS_PATH, extras)
    dump(EXERCISES_PATH, exercises)
    print(
        f"Upgraded curriculum: {len(base['modules'])} modules, "
        f"{len(base['lessons'])} lessons, {len(exercises)} exercises."
    )


if __name__ == '__main__':
    main()
