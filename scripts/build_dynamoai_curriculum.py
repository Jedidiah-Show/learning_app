#!/usr/bin/env python3
"""Legacy importer from the original Complete Lesson Guides PDF.

The web application reads the maintained JSON curriculum. That file now
contains editorial updates that are not present in the original PDF, so this
importer will overwrite those updates if run before the PDF is refreshed.
Use it only when rebuilding the app data from an updated PDF source.

Usage:
    python scripts/build_dynamoai_curriculum.py
    python scripts/build_dynamoai_curriculum.py path/to/guides.pdf
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = ROOT / "DynamoAI_Curriculum_Complete_Lesson_Guides.pdf"
OUTPUT = ROOT / "app" / "data" / "dynamoai_curriculum.json"

MODULE_RE = re.compile(
    r"^MODULE\s+(\d{2})\s+·\s+(\d+)\s+LESSONS\s+·\s+PAGES\s+([\d–-]+)\s*$",
    re.MULTILINE,
)
LESSON_RE = re.compile(
    r"^(?:MODULE\s+(\d{2})\s+·\s+)?LESSON\s+(\d+\.\d+)\s+·\s+PAGE\s+(\d)\s+OF\s+3[^\n]*$",
    re.MULTILINE,
)
PAGE_FOOTER_RE = re.compile(
    r"\n\s*Three pages per lesson\s+Page \d+ of \d+\s*$"
)
PAGE_HEADER_RE = re.compile(
    r"^DYNAMOAI\s*·\s*COMPASS AI\s+Complete lesson guides\s*·\s*\d+\s+lessons\s*$",
    re.MULTILINE,
)

SECTION_HEADINGS = (
    "WHY THIS LESSON MATTERS",
    "WHAT YOU WILL BE ABLE TO DO",
    "CORE CONCEPTS",
    "KEY TERMS",
    "MENTAL MODEL",
    "WORKED EXAMPLE",
    "STEP BY STEP",
    "CODE",
    "WHAT TO NOTICE",
    "COMMON MISTAKES",
    "PRODUCTION NOTES",
    "CHECKPOINT CHECKLIST",
    "SHORT QUESTIONS",
    "TASKS",
    "CAPSTONE CONNECTION",
)
HEADING_RE = re.compile(
    r"^(?:" + "|".join(re.escape(item) for item in SECTION_HEADINGS) + r")\s*$",
    re.MULTILINE,
)
INLINE_HEADING_RE = re.compile(
    r"[ \t]+(" + "|".join(re.escape(item) for item in SECTION_HEADINGS) + r")[ \t]+"
)
LESSON_TITLE_RE = re.compile(
    r"^(?:\s*[A-Z][A-Z0-9 .&/,:()'\-]+)$", re.MULTILINE
)


def extract_text(pdf: Path) -> str:
    completed = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def clean_page(text: str) -> str:
    text = PAGE_HEADER_RE.sub("", text)
    text = PAGE_FOOTER_RE.sub("", text)
    text = text.replace("\f", "\n")
    # PDF extraction sometimes puts a section heading immediately after the
    # previous sentence instead of on its own line. Split those headings before
    # the rest of the importer looks for whole-line markers.
    text = INLINE_HEADING_RE.sub(lambda match: f"\n{match.group(1)}\n", text)
    lines = [line.rstrip() for line in text.splitlines()]
    # Remove the repeated running header (lesson x.y · page n of 3 · module).
    lines = [
        line for line in lines
        if not re.match(r"^LESSON\s+\d+\.\d+\s+·\s+PAGE\s+\d\s+OF\s+3\s+", line)
    ]
    text = "\n".join(lines)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_sections(page: str) -> dict[str, str]:
    matches = list(HEADING_RE.finditer(page))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(page)
        sections[match.group(0).strip()] = page[start:end].strip()
    return sections


def bullet_lines(text: str) -> list[str]:
    """Return bullet/numbered items while joining wrapped continuation lines."""
    items: list[str] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.match(r"^(?:[•◆□→]|\d+\.)\s+", line):
            if current:
                items.append(collapse(" ".join(current)))
            current = [re.sub(r"^(?:[•◆□→]|\d+\.)\s+", "", line)]
        elif current:
            current.append(line)
        elif items:
            # A stray continuation of the previous item.
            items[-1] = collapse(f"{items[-1]} {line}")
    if current:
        items.append(collapse(" ".join(current)))
    return [item for item in items if item]


def paragraphs(text: str) -> list[str]:
    chunks = re.split(r"\n\s*\n", text)
    return [collapse(chunk) for chunk in chunks if collapse(chunk)]


def parse_core_concepts(text: str) -> list[dict[str, str]]:
    concepts: list[dict[str, str]] = []
    blocks = [item for item in re.split(r"\n\s*\n", text) if item.strip()]
    for block in blocks:
        lines = [collapse(line) for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        # A concept is usually a short title line followed by its explanation.
        if (
            len(lines) > 1
            and len(lines[0]) <= 80
            and not lines[0].startswith("•")
            and not lines[0].endswith((".", "?", "!", ":", ";"))
        ):
            concepts.append({
                "title": lines[0],
                "content": collapse(" ".join(lines[1:])),
            })
        else:
            content = collapse(" ".join(lines))
            concepts.append({"title": "Concept", "content": content})
    return concepts


def parse_key_terms(text: str) -> list[dict[str, str]]:
    terms: list[dict[str, str]] = []
    current: list[str] = []
    # A missing blank line can leave the next section heading in this block.
    text = re.split(
        r"\n\s*(?:MENTAL MODEL|CAPSTONE CONNECTION|YOUR WORKING NOTES)\b",
        text,
        maxsplit=1,
    )[0]
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line in SECTION_HEADINGS:
            break
        # Terms are indented labels followed by a wide column of definition.
        match = re.match(r"^([A-Z][A-Za-z0-9 /&()'.,+-]{1,60}?)\s{2,}(.+)$", line)
        if match:
            if current:
                terms.append(_term(current))
            current = [match.group(1).strip(), match.group(2).strip()]
        elif current:
            current[1] = collapse(f"{current[1]} {line}")
    if current:
        terms.append(_term(current))
    return terms


def _term(parts: list[str]) -> dict[str, str]:
    return {"term": collapse(parts[0]), "definition": collapse(parts[1])}


def parse_code(text: str) -> dict[str, str] | None:
    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return None
    description = ""
    code_lines: list[str] = []
    seen_code = False
    for line in lines:
        stripped = line.strip()
        if not seen_code and not stripped:
            continue
        if not seen_code and not code_lines and not re.match(
            r"^(?:import |from |[A-Za-z_][A-Za-z0-9_]*\s*=|def |class |@|#|const |let |var |async |await |if |for |while |try:|SELECT|CREATE|curl |git |pip |uv |python |print\()",
            stripped,
        ):
            description = collapse(f"{description} {stripped}")
            continue
        seen_code = True
        code_lines.append(line)
    code = textwrap.dedent("\n".join(code_lines)).rstrip()
    if not code and description:
        return None
    return {"title": description or "Worked code", "code": code}


def detect_language(code: str) -> str:
    """Best-effort language label for a parsed snippet."""
    if re.search(r"^\s*(?:import |from |def |class |async def )", code, re.MULTILINE):
        return "python"
    if re.search(r"\b(?:SELECT|INSERT|UPDATE|DELETE|CREATE TABLE)\b", code, re.IGNORECASE):
        return "sql"
    if re.search(r"^\s*(?:curl|git|pip|uv|python|docker|kubectl)\b", code, re.MULTILINE):
        return "shell"
    if re.search(r"\b(?:interface|type|const|let|function)\b", code):
        return "typescript"
    return "text"


def parse_lesson(lesson_id: str, module_id: str, pages: list[str]) -> dict:
    first = split_sections(pages[0])
    second = split_sections(pages[1])
    third = split_sections(pages[2])

    title = ""
    subtitle = ""
    meta = ""
    reason = first.get("WHY THIS LESSON MATTERS", "")
    if reason:
        before = pages[0].split("WHY THIS LESSON MATTERS", 1)[0]
        lines = [collapse(line) for line in before.splitlines() if collapse(line)]
        # Remove residual running-header text.
        lines = [
            line for line in lines
            if not line.startswith("DYNAMOAI")
            and not line.startswith("LESSON ")
            and not re.fullmatch(r"(?:Understand|Build|Operate) it", line)
        ]
        if lines:
            title = lines[0]
        meta_index = next(
            (index for index, line in enumerate(lines[1:], start=1) if "· Lesson" in line),
            None,
        )
        subtitle_lines = lines[1:meta_index] if meta_index is not None else lines[1:]
        subtitle = " ".join(subtitle_lines).strip()
        if meta_index is not None:
            meta = lines[meta_index]

    code = parse_code(second.get("CODE", ""))
    if code:
        code["language"] = detect_language(code["code"])
        notice = second.get("WHAT TO NOTICE", "")
        code["what_to_notice"] = bullet_lines(notice)

    core_concepts = parse_core_concepts(first.get("CORE CONCEPTS", ""))
    terms = parse_key_terms(first.get("KEY TERMS", ""))
    mental_model = collapse(first.get("MENTAL MODEL", ""))
    capstone = collapse(third.get("CAPSTONE CONNECTION", ""))
    if not capstone:
        match = re.search(
            r"CAPSTONE CONNECTION\s+(.+?)(?=\n\s*(?:YOUR WORKING NOTES|$))",
            pages[2],
            re.DOTALL,
        )
        capstone = collapse(match.group(1)) if match else ""

    lesson = {
        "id": lesson_id,
        "module_id": module_id,
        "title": title or f"Lesson {lesson_id}",
        "subtitle": subtitle,
        "meta": meta,
        "why_it_matters": paragraphs(reason),
        "outcomes": bullet_lines(first.get("WHAT YOU WILL BE ABLE TO DO", "")),
        "core_concepts": core_concepts,
        "key_terms": terms,
        "mental_model": mental_model,
        "worked_example": paragraphs(second.get("WORKED EXAMPLE", "")),
        "steps": bullet_lines(second.get("STEP BY STEP", "")),
        "code": code,
        "common_mistakes": bullet_lines(third.get("COMMON MISTAKES", "")),
        "production_notes": bullet_lines(third.get("PRODUCTION NOTES", "")),
        "checklist": bullet_lines(third.get("CHECKPOINT CHECKLIST", "")),
        "questions": bullet_lines(third.get("SHORT QUESTIONS", "")),
        "tasks": bullet_lines(third.get("TASKS", "")),
        "capstone": capstone,
        "pages": [pages[0], pages[1], pages[2]],
    }
    return lesson


def parse_module_intro(text: str, number: str, lesson_count: str, pages: str) -> dict:
    sections = split_sections(text)
    before = text
    for heading in SECTION_HEADINGS:
        before = before.split(heading, 1)[0]
    lines = [collapse(line) for line in before.splitlines() if collapse(line)]
    lines = [
        line for line in lines
        if not line.startswith("DYNAMOAI")
        and not re.match(r"^MODULE\s+\d{2}\s+·", line)
    ]
    title = lines[0] if lines else f"Module {number}"
    description = lines[1] if len(lines) > 1 else ""
    project_match = re.search(
        r"MODULE PROJECT\s+(.+?)(?:\n\s*\n|\nThree pages|\Z)", text, re.DOTALL
    )
    project = collapse(project_match.group(1)) if project_match else ""
    return {
        "id": number,
        "number": int(number),
        "title": title,
        "description": description,
        "lesson_count": int(lesson_count),
        "pages": pages,
        "what_you_will_build": paragraphs(
            sections.get("WHAT YOU WILL BUILD", "")
        ),
        "before_you_start": paragraphs(
            sections.get("BEFORE YOU START", "")
        ),
        "outcomes": bullet_lines(
            sections.get("LEARNING OUTCOMES", "")
        ),
        "questions": bullet_lines(
            sections.get("QUESTIONS THIS MODULE ANSWERS", "")
        ),
        "project": project,
    }


def build(pdf: Path) -> dict:
    text = extract_text(pdf)
    lesson_matches = list(LESSON_RE.finditer(text))
    module_matches = list(MODULE_RE.finditer(text))
    lesson_ids = {match.group(2) for match in lesson_matches}
    if not lesson_ids:
        raise SystemExit("No lessons were found in the PDF")
    if not module_matches:
        raise SystemExit("No modules were found in the PDF")

    # Group lesson page matches by lesson id.
    lesson_pages: dict[str, list[str]] = {}
    for index, match in enumerate(lesson_matches):
        lesson_id = match.group(2)
        end = (
            lesson_matches[index + 1].start()
            if index + 1 < len(lesson_matches)
            else len(text)
        )
        page_text = clean_page(text[match.end():end])
        lesson_pages.setdefault(lesson_id, []).append(page_text)

    lessons = []
    by_module: dict[str, list[dict]] = {}
    for lesson_id in sorted(lesson_pages, key=lambda value: tuple(
        int(part) for part in value.split(".")
    )):
        pages = lesson_pages[lesson_id]
        if len(pages) != 3:
            raise SystemExit(
                f"Lesson {lesson_id} has {len(pages)} pages instead of 3"
            )
        lesson = parse_lesson(lesson_id, lesson_id.split(".")[0].zfill(2), pages)
        lessons.append(lesson)
        by_module.setdefault(lesson["module_id"], []).append(lesson)

    modules = []
    for match in module_matches:
        number = match.group(1)
        first_lesson = next(
            (
                item for item in lesson_matches
                if item.group(2).split(".")[0] == str(int(number))
            ),
            None,
        )
        end = first_lesson.start() if first_lesson else len(text)
        intro = text[match.end():end]
        module = parse_module_intro(
            intro, number, match.group(2), match.group(3)
        )
        module["lessons"] = by_module.get(number, [])
        modules.append(module)

    if sum(len(module["lessons"]) for module in modules) != len(lessons):
        raise SystemExit("Lessons were not assigned to every module")

    return {
        "course": {
            "id": "dynamoai",
            "title": "DynamoAI: AI Engineering",
            "subtitle": "From AI Ideas to Production Systems",
            "description": (
                f"A {len(modules)}-module, {len(lessons)}-lesson course that builds "
                "a production AI platform from Python and backend engineering "
                "through RAG, agents, MCP, and deployment."
            ),
            "total_lessons": len(lessons),
        },
        "modules": modules,
        "lessons": lessons,
    }


def main() -> None:
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF
    if not pdf.exists():
        raise SystemExit(f"Curriculum PDF not found: {pdf}")
    data = build(pdf)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {len(data['lessons'])} lessons in "
        f"{len(data['modules'])} modules to {OUTPUT}"
    )
    for module in data["modules"]:
        print(
            f"  Module {module['id']}: {module['title']} "
            f"({len(module['lessons'])} lessons)"
        )


if __name__ == "__main__":
    main()
