"""Read-only access to the versioned RUACH course bundled with the app."""

from functools import lru_cache
import json
import re
from pathlib import Path

from app.videos import build_lesson_video


CURRICULUM_PATH = Path(__file__).parent / 'data' / 'dynamoai_curriculum.json'
EXTRAS_PATH = Path(__file__).parent / 'data' / 'lesson_extras.json'

# The bundled source pages mark major sections with short uppercase lines and
# each core concept with a title-case sub-heading. Rebuilding those blocks lets
# the lesson page show three focused explanations instead of one wall of text.
_SECTION_LINE = re.compile(r"^[A-Z][A-Z0-9 &/,()'\-]{2,69}$")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")


def _is_page_heading(line):
    text = line.strip()
    return (
        bool(_SECTION_LINE.match(text))
        and any(char.isalpha() for char in text)
        and not text.startswith(('\u2022', '-'))
    )


def _page_sections(pages):
    """Split the source page text into ``{heading: [lines]}`` blocks."""
    sections = {}
    current = None
    for raw in '\n'.join(pages or []).split('\n'):
        if _is_page_heading(raw):
            current = raw.strip()
            sections.setdefault(current, [])
        elif current is not None:
            sections[current].append(raw)
    return sections


def _looks_like_subheading(text, buffer_text, previous_text):
    if len(text) > 75 or len(text.split()) > 10:
        return False
    if text.endswith(('.', ',', ';', ':', '!', '?', '"', ')', ']')):
        return False
    if text.startswith(('\u2022', '-')) or text[0].isdigit():
        return False
    if buffer_text and previous_text and not previous_text.rstrip().endswith(
        ('.', ':', ';', '!', '?', ')', '"')
    ):
        return False
    return True


def _split_paragraph(text, max_sentences=3, max_chars=360):
    """Break a dense paragraph into beginner-sized chunks."""
    text = ' '.join(text.split())
    if not text:
        return []
    sentences = [part.strip() for part in _SENTENCE_SPLIT.split(text) if part.strip()]
    if len(sentences) <= 1:
        return [text]
    paragraphs = []
    current = []
    for sentence in sentences:
        candidate = ' '.join(current + [sentence])
        if current and (len(current) >= max_sentences or len(candidate) > max_chars):
            paragraphs.append(' '.join(current))
            current = [sentence]
        else:
            current.append(sentence)
    if current:
        paragraphs.append(' '.join(current))
    return paragraphs


def _concept_blocks(lines):
    """Turn wrapped page lines into heading, paragraph, and bullet blocks."""
    blocks = []
    buffer = []
    previous = None

    def flush():
        nonlocal previous
        if buffer:
            previous = ' '.join(buffer)
            blocks.append(('para', previous))
            buffer.clear()

    for raw in lines:
        text = raw.strip()
        if not text:
            flush()
            continue
        if text.startswith(('\u2022', '- ')):
            flush()
            blocks.append(('bullet', text.lstrip('\u2022- ').strip()))
            continue
        if _looks_like_subheading(text, bool(buffer), previous):
            flush()
            blocks.append(('heading', text))
            previous = None
            continue
        buffer.append(text)
    flush()
    return blocks


def _concept_sections(lines):
    """Group a CORE CONCEPTS block into titled concepts with readable chunks."""
    concepts = []
    for kind, text in _concept_blocks(lines):
        if kind == 'heading':
            concepts.append({'title': text, 'paragraphs': [], 'bullets': []})
            continue
        if not concepts:
            concepts.append({'title': 'Concept', 'paragraphs': [], 'bullets': []})
        if kind == 'para':
            concepts[-1]['paragraphs'].extend(_split_paragraph(text))
        else:
            concepts[-1]['bullets'].append(text)
    return [
        concept for concept in concepts
        if concept['paragraphs'] or concept['bullets']
    ]


_ABBREVIATIONS = ('e.g.', 'i.e.', 'etc.', 'vs.', 'mr.', 'mrs.', 'ms.', 'dr.')


def _first_sentence(text):
    """Return the opening sentence, ignoring common abbreviations."""
    for match in re.finditer(r'[.!?](?=\s|$)', text):
        sentence = text[:match.end()]
        if sentence.lower().endswith(_ABBREVIATIONS):
            continue
        return sentence.strip()
    return text.strip()


def _with_key_ideas(concepts):
    """Pull the first sentence of each concept out as a one-line key idea."""
    for concept in concepts:
        paragraphs = concept.get('paragraphs') or []
        if not paragraphs:
            concept['key_idea'] = ''
            continue
        opening = paragraphs[0]
        key_idea = _first_sentence(opening)
        remainder = opening[len(key_idea):].strip()
        concept['key_idea'] = key_idea
        concept['paragraphs'] = ([remainder] if remainder else []) + paragraphs[1:]
    return concepts


def _lesson_concepts(lesson):
    lines = _page_sections(lesson.get('pages')).get('CORE CONCEPTS')
    if not lines:
        return _with_key_ideas([
            {
                'title': concept.get('title') or 'Concept',
                'paragraphs': _split_paragraph(concept.get('content', '')),
                'bullets': [],
            }
            for concept in lesson.get('core_concepts') or []
            if isinstance(concept, dict)
        ])
    return _with_key_ideas(_concept_sections(lines))


def _reading_minutes(lesson):
    """Rough study time: reading prose plus a little time for the exercises."""
    words = 0
    for page in lesson.get('pages') or []:
        words += len(str(page).split())
    reading = max(1, round(words / 180))
    activities = 3 if lesson.get('tasks') else 2
    return reading + activities


def _lesson_extras():
    """Load the plain-language layer and self-check answer key, if present."""
    if not EXTRAS_PATH.exists():
        return {}
    try:
        with EXTRAS_PATH.open(encoding='utf-8') as source:
            data = json.load(source)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _attach_extras(lesson, extras):
    entry = extras.get(lesson.get('id'))
    if not isinstance(entry, dict):
        lesson['extras'] = None
        lesson['question_answers'] = []
        return
    answers = entry.get('answers')
    answers = answers if isinstance(answers, list) else []
    questions = lesson.get('questions') or []
    # Keep answers aligned with the rendered questions even if the generated
    # list is short or long.
    lesson['question_answers'] = [
        str(answers[index]) if index < len(answers) and answers[index] else ''
        for index in range(len(questions))
    ]
    lesson['extras'] = {
        'intro': entry.get('intro') or '',
        'concepts': entry.get('concepts') if isinstance(
            entry.get('concepts'), list
        ) else [],
    }


@lru_cache(maxsize=1)
def curriculum():
    with CURRICULUM_PATH.open(encoding='utf-8') as source:
        data = json.load(source)
    data['course']['title'] = 'RUACH AI Engineering'
    data['course']['description'] = (
        'The RUACH AI Engineering course: 13 modules and 201 lessons, '
        'from Python and backend engineering through multimodal, retrieval, '
        'agent, security, evaluation, governance, and production AI systems.'
    )
    resources_path = Path(__file__).parent / 'data' / 'dynamoai_resources.json'
    with resources_path.open(encoding='utf-8') as source:
        resources = json.load(source)
    modules = data.get('modules', [])
    lessons = data.get('lessons', [])
    if len(lessons) != data.get('course', {}).get('total_lessons'):
        raise ValueError('RUACH curriculum lesson count does not match its manifest')
    module_ids = {module['id'] for module in modules}
    if any(lesson.get('module_id') not in module_ids for lesson in lessons):
        raise ValueError('RUACH curriculum contains a lesson with an unknown module')
    data['_module_map'] = {module['id']: module for module in modules}
    data['_lesson_map'] = {lesson['id']: lesson for lesson in lessons}
    extras = _lesson_extras()
    for module in modules:
        module['resources'] = resources.get(f"module:{module['id']}", {})
    for index, lesson in enumerate(lessons):
        lesson['_ordinal'] = index + 1
        lesson['_module'] = data['_module_map'][lesson['module_id']]
        lesson['resources'] = resources.get(lesson['id'], {})
        lesson['video'] = build_lesson_video(lesson['resources'].get('video'))
        lesson['concepts'] = _lesson_concepts(lesson)
        lesson['reading_minutes'] = _reading_minutes(lesson)
        _attach_extras(lesson, extras)
    return data


def all_modules():
    return curriculum()['modules']


def all_lessons():
    return curriculum()['lessons']


def get_module(module_id):
    return curriculum()['_module_map'].get(str(module_id))


def get_lesson(lesson_id):
    return curriculum()['_lesson_map'].get(str(lesson_id))


def lesson_ordinal(lesson_id):
    lesson = get_lesson(lesson_id)
    return lesson['_ordinal'] if lesson else None


def module_lessons(module_id):
    module = get_module(module_id)
    return module['lessons'] if module else []


def readable_paragraphs(text):
    """Template helper: split dense prose into beginner-sized paragraphs."""
    if not isinstance(text, str):
        return [text] if text else []
    return _split_paragraph(text)


def lesson_context(lesson):
    """Return structured lesson material without duplicated PDF page text."""
    excluded = {
        'pages', '_ordinal', '_module', 'video', 'concepts', 'reading_minutes',
        'extras', 'question_answers',
    }
    return {key: value for key, value in lesson.items() if key not in excluded}
