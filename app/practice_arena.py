"""Practice Arena catalogue, taxonomy, and public problem serialisation.

The Arena intentionally builds on the curated lesson exercises while keeping
lesson practice untouched. Public problem payloads omit judge checks and
reference solutions; completion is recorded only after an authoritative
server-side verdict.
"""

from functools import lru_cache
import ast
import json
from pathlib import Path

from app.practice import all_practice_exercises


ARENA_PATH = Path(__file__).parent / 'data' / 'arena_problems.json'

TRACKS = (
    {
        'id': 'ai-engineering',
        'name': 'AI Engineering Practice',
        'short_name': 'AI Engineering',
        'tagline': 'Build the Python, data, API, LLM, RAG, agent, evaluation, '
                   'security and deployment skills real AI systems demand.',
        'primary': True,
    },
    {
        'id': 'algorithms',
        'name': 'Algorithms & Problem Solving',
        'short_name': 'Algorithms',
        'tagline': 'Sharpen computational thinking with arrays, strings, '
                   'searching, sorting, recursion and data structures.',
        'primary': False,
    },
    {
        'id': 'machine-learning',
        'name': 'Machine Learning Practice',
        'short_name': 'Machine Learning',
        'tagline': 'Work with data, probability, and models using the Python '
                   'standard library before reaching for ML packages.',
        'primary': False,
    },
)

TOPICS = (
    {'id': 'foundations', 'track': 'ai-engineering', 'name': 'Foundations'},
    {'id': 'python', 'track': 'ai-engineering', 'name': 'Python'},
    {'id': 'backend', 'track': 'ai-engineering', 'name': 'Backend & APIs'},
    {'id': 'llm-applications', 'track': 'ai-engineering', 'name': 'LLM Applications'},
    {'id': 'evaluation', 'track': 'ai-engineering', 'name': 'Evaluation'},
    {'id': 'rag-retrieval', 'track': 'ai-engineering', 'name': 'RAG & Retrieval'},
    {'id': 'agents', 'track': 'ai-engineering', 'name': 'Agents & Tool Use'},
    {'id': 'orchestration', 'track': 'ai-engineering', 'name': 'Orchestration'},
    {'id': 'mcp', 'track': 'ai-engineering', 'name': 'MCP'},
    {'id': 'production', 'track': 'ai-engineering', 'name': 'Production & Security'},
    {'id': 'deployment', 'track': 'ai-engineering', 'name': 'Deployment'},
    {'id': 'system-design', 'track': 'ai-engineering', 'name': 'System Design'},
    {'id': 'capstone', 'track': 'ai-engineering', 'name': 'Capstone'},
    {'id': 'arrays-strings', 'track': 'algorithms', 'name': 'Arrays & Strings'},
    {'id': 'dictionaries-sets', 'track': 'algorithms', 'name': 'Dictionaries & Sets'},
    {'id': 'searching', 'track': 'algorithms', 'name': 'Searching'},
    {'id': 'sorting', 'track': 'algorithms', 'name': 'Sorting & Complexity'},
    {'id': 'recursion', 'track': 'algorithms', 'name': 'Recursion'},
    {'id': 'stacks-queues', 'track': 'algorithms', 'name': 'Stacks & Queues'},
    {'id': 'mixed', 'track': 'algorithms', 'name': 'Mixed Challenges'},
    {'id': 'statistics', 'track': 'machine-learning', 'name': 'Statistics'},
)

DIFFICULTIES = ('beginner', 'intermediate', 'advanced')
DIFFICULTY_ORDER = {name: index for index, name in enumerate(DIFFICULTIES)}

# Lesson module number -> Arena topic.  The lesson id prefix is stable in the
# shared curriculum, so this keeps classification auditable without duplicating
# a topic string on all 62 legacy exercises.
LESSON_MODULE_TOPICS = {
    0: 'foundations',
    1: 'python',
    2: 'backend',
    3: 'llm-applications',
    4: 'evaluation',
    5: 'rag-retrieval',
    6: 'agents',
    7: 'orchestration',
    8: 'mcp',
    9: 'production',
    10: 'deployment',
    11: 'system-design',
    12: 'capstone',
}

REQUIRED_PROBLEM_FIELDS = {
    'id', 'track', 'topic', 'title', 'summary', 'statement',
    'difficulty', 'skills', 'prerequisites', 'starter_code',
    'solution_code', 'browser_checks', 'estimated_minutes',
}


def _topic_ids(track):
    return {topic['id'] for topic in TOPICS if topic['track'] == track}


def topic_for_lesson(lesson_id):
    """Return the Arena topic for a curriculum lesson id such as ``1.01``."""
    try:
        module_number = int(str(lesson_id).split('.', 1)[0])
    except (TypeError, ValueError):
        return 'foundations'
    return LESSON_MODULE_TOPICS.get(module_number, 'foundations')


def _legacy_problem(exercise):
    return {
        'id': exercise['id'],
        'source': 'lesson',
        'lesson_id': exercise['lesson_id'],
        'track': 'ai-engineering',
        'topic': topic_for_lesson(exercise['lesson_id']),
        'title': exercise['title'],
        'summary': exercise['instructions'],
        'statement': exercise['instructions'],
        'examples': [],
        'constraints': [],
        'difficulty': exercise['difficulty'],
        'skills': list(exercise['skills']),
        'prerequisites': list(exercise['prerequisites']),
        'estimated_minutes': exercise.get('estimated_minutes', 20),
        'starter_code': exercise['starter_code'],
        'solution_code': exercise.get('solution_code', ''),
        'browser_checks': exercise['checks_code'],
        'hints': [],
        'editorial': '',
    }


def _validate_problem(problem, seen_ids):
    missing = REQUIRED_PROBLEM_FIELDS - set(problem)
    if missing:
        raise ValueError(
            f"Arena problem {problem.get('id', '<unknown>')} is missing "
            f"fields: {', '.join(sorted(missing))}"
        )
    problem_id = problem['id']
    if not isinstance(problem_id, str) or not problem_id.strip():
        raise ValueError('Arena problem IDs must be non-empty strings')
    if problem_id in seen_ids:
        raise ValueError(f'Duplicate Arena problem ID: {problem_id}')
    if problem['track'] not in {track['id'] for track in TRACKS}:
        raise ValueError(f"Arena problem {problem_id} has an unknown track")
    if problem['topic'] not in _topic_ids(problem['track']):
        raise ValueError(f"Arena problem {problem_id} has an unknown topic")
    if problem['difficulty'] not in DIFFICULTIES:
        raise ValueError(f"Arena problem {problem_id} has an invalid difficulty")
    for field in ('title', 'summary', 'statement', 'starter_code',
                  'solution_code', 'browser_checks'):
        if not isinstance(problem[field], str) or not problem[field].strip():
            raise ValueError(f"Arena problem {problem_id} has an empty {field}")
    for field in ('skills', 'prerequisites'):
        if (
            not isinstance(problem[field], list)
            or any(not isinstance(item, str) or not item for item in problem[field])
        ):
            raise ValueError(f"Arena problem {problem_id} has invalid {field}")
    if not problem['skills']:
        raise ValueError(f"Arena problem {problem_id} needs at least one skill")
    if not isinstance(problem['estimated_minutes'], int) or problem['estimated_minutes'] <= 0:
        raise ValueError(f"Arena problem {problem_id} has invalid estimated_minutes")
    if not isinstance(problem['examples'], list):
        raise ValueError(f"Arena problem {problem_id} has invalid examples")
    if not isinstance(problem['constraints'], list):
        raise ValueError(f"Arena problem {problem_id} has invalid constraints")
    if not isinstance(problem['hints'], list):
        raise ValueError(f"Arena problem {problem_id} has invalid hints")
    if not isinstance(problem['editorial'], str):
        raise ValueError(f"Arena problem {problem_id} has invalid editorial")
    # Compiling here catches broken starter code or checks at import time,
    # before a learner ever opens the workspace.
    for field in ('starter_code', 'solution_code', 'browser_checks'):
        try:
            compile(
                problem[field], f'{problem_id}:{field}', 'exec',
                flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
            )
        except SyntaxError as error:
            raise ValueError(
                f'Arena problem {problem_id} has invalid {field}: {error}'
            ) from error


@lru_cache(maxsize=1)
def all_arena_problems():
    """Return every published Arena problem keyed by id, in curriculum order."""
    by_id = {}
    for exercise in all_practice_exercises().values():
        problem = _legacy_problem(exercise)
        _validate_problem(problem, by_id)
        by_id[problem['id']] = problem

    if ARENA_PATH.exists():
        with ARENA_PATH.open(encoding='utf-8') as source:
            arena_only = json.load(source)
        if not isinstance(arena_only, list):
            raise ValueError('Arena problems must be a JSON list')
        for raw in arena_only:
            if not isinstance(raw, dict):
                raise ValueError('Arena problems must be JSON objects')
            problem = {
                'source': 'arena',
                'lesson_id': raw.get('lesson_id'),
                'examples': raw.get('examples', []),
                'constraints': raw.get('constraints', []),
                'hints': raw.get('hints', []),
                'editorial': raw.get('editorial', ''),
                **raw,
            }
            _validate_problem(problem, by_id)
            by_id[problem['id']] = problem

    for problem in by_id.values():
        for prerequisite in problem['prerequisites']:
            if prerequisite not in by_id:
                raise ValueError(
                    f"Arena problem {problem['id']} has an unknown prerequisite "
                    f"{prerequisite}"
                )
            if prerequisite == problem['id']:
                raise ValueError(
                    f"Arena problem {problem['id']} cannot require itself"
                )
    _assert_acyclic(by_id)
    return by_id


def _assert_acyclic(by_id):
    state = {}

    def visit(problem_id):
        if state.get(problem_id) == 'visiting':
            raise ValueError(f'Arena prerequisite cycle includes {problem_id}')
        if state.get(problem_id) == 'done':
            return
        state[problem_id] = 'visiting'
        for prerequisite in by_id[problem_id]['prerequisites']:
            visit(prerequisite)
        state[problem_id] = 'done'

    for problem_id in by_id:
        visit(problem_id)


def get_arena_problem(problem_id):
    return all_arena_problems().get(str(problem_id))


def topic_by_id(topic_id):
    return next((topic for topic in TOPICS if topic['id'] == topic_id), None)


def track_by_id(track_id):
    return next((track for track in TRACKS if track['id'] == track_id), None)


def track_topics(track_id):
    return [topic for topic in TOPICS if topic['track'] == track_id]


def problem_prerequisites(problem):
    """Return prerequisite problems in a stable, displayable order."""
    by_id = all_arena_problems()
    return [
        by_id[prerequisite]
        for prerequisite in problem['prerequisites']
        if prerequisite in by_id
    ]


def public_problem(problem):
    """Serialise only material safe to send to the learner's browser."""
    return {
        'id': problem['id'],
        'source': problem['source'],
        'lesson_id': problem['lesson_id'],
        'track': problem['track'],
        'track_name': track_by_id(problem['track'])['name'],
        'topic': problem['topic'],
        'topic_name': (topic_by_id(problem['topic']) or {}).get('name', ''),
        'title': problem['title'],
        'summary': problem['summary'],
        'statement': problem['statement'],
        'examples': problem['examples'],
        'constraints': problem['constraints'],
        'difficulty': problem['difficulty'],
        'skills': problem['skills'],
        'prerequisites': problem['prerequisites'],
        'estimated_minutes': problem['estimated_minutes'],
        'starter_code': problem['starter_code'],
        'has_editorial': bool(problem['solution_code'] or problem['editorial']),
    }


def editorial_payload(problem):
    """Reference material returned only after an explicit learner reveal."""
    return {
        'solution_code': problem['solution_code'],
        'editorial': problem['editorial'],
    }


def _matches_query(problem, query):
    if not query:
        return True
    haystack = ' '.join([
        problem['title'],
        problem['summary'],
        problem['statement'],
        problem['topic'],
        ' '.join(problem['skills']),
    ]).lower()
    return all(term in haystack for term in query.lower().split())


def filter_problems(problems, track=None, topic=None, difficulty=None,
                    skill=None, query=None):
    """Apply the catalogue filters in a predictable, composable order."""
    result = list(problems)
    if track:
        result = [item for item in result if item['track'] == track]
    if topic:
        result = [item for item in result if item['topic'] == topic]
    if difficulty:
        if isinstance(difficulty, list):
            result = [item for item in result if item['difficulty'] in difficulty]
        else:
            result = [
                item for item in result if item['difficulty'] == difficulty
            ]
    if skill:
        result = [item for item in result if skill in item['skills']]
    if query:
        result = [item for item in result if _matches_query(item, query)]
    return result


def sort_problems(problems, sort='recommended'):
    if sort == 'difficulty':
        return sorted(
            problems,
            key=lambda item: (
                DIFFICULTY_ORDER[item['difficulty']],
                item['title'].lower(),
            ),
        )
    if sort == 'title':
        return sorted(problems, key=lambda item: item['title'].lower())
    if sort == 'time':
        return sorted(
            problems,
            key=lambda item: (item['estimated_minutes'], item['title'].lower()),
        )
    track_order = {track['id']: index for index, track in enumerate(TRACKS)}
    topic_order = {topic['id']: index for index, topic in enumerate(TOPICS)}
    return sorted(
        problems,
        key=lambda item: (
            track_order.get(item['track'], 99),
            topic_order.get(item['topic'], 99),
            DIFFICULTY_ORDER[item['difficulty']],
            item['title'].lower(),
        ),
    )


def available_filters(problems):
    skills = sorted({skill for item in problems for skill in item['skills']})
    tracks = [
        {
            **track,
            'count': sum(1 for item in problems if item['track'] == track['id']),
        }
        for track in TRACKS
    ]
    topics = [
        {
            **topic,
            'count': sum(1 for item in problems if item['topic'] == topic['id']),
        }
        for topic in TOPICS
    ]
    return {
        'tracks': tracks,
        'topics': topics,
        'difficulties': list(DIFFICULTIES),
        'skills': skills,
    }


def catalogue(track=None, topic=None, difficulty=None, skill=None,
              query=None, sort='recommended'):
    """Return filtered/sorted problems plus the metadata needed to render."""
    all_problems = list(all_arena_problems().values())
    filters = available_filters(all_problems)
    valid_tracks = {item['id'] for item in TRACKS}
    valid_topics = {item['id'] for item in TOPICS}
    if track not in valid_tracks:
        track = None
    if topic not in valid_topics:
        topic = None
    if difficulty:
        if isinstance(difficulty, list):
            # Validate all difficulties in the list
            difficulty = [d for d in difficulty if d in DIFFICULTIES]
            if not difficulty:
                difficulty = None
        elif difficulty not in DIFFICULTIES:
            difficulty = None
    if skill not in filters['skills']:
        skill = None
    if sort not in {'recommended', 'difficulty', 'title', 'time'}:
        sort = 'recommended'
    query = (query or '').strip()[:120]
    result = sort_problems(
        filter_problems(
            all_problems,
            track=track,
            topic=topic,
            difficulty=difficulty,
            skill=skill,
            query=query,
        ),
        sort=sort,
    )
    # Build selected difficulties display
    # Maintain backward compatibility: return '' when difficulty is None/invalid,
    # string when single difficulty, list when multiple difficulties
    if difficulty is None:
        selected_difficulty = ''
    elif isinstance(difficulty, list):
        selected_difficulty = difficulty
    else:
        selected_difficulty = difficulty  # single valid string
    return {
        'problems': result,
        'filters': filters,
        'selected': {
            'track': track or '',
            'topic': topic or '',
            'difficulty': selected_difficulty,
            'skill': skill or '',
            'query': query,
            'sort': sort,
        },
    }


def stats_for_track(problems, track_id):
    scoped = [item for item in problems if item['track'] == track_id]
    return {
        'total': len(scoped),
        'beginner': sum(
            1 for item in scoped if item['difficulty'] == 'beginner'
        ),
        'intermediate': sum(
            1 for item in scoped if item['difficulty'] == 'intermediate'
        ),
        'advanced': sum(
            1 for item in scoped if item['difficulty'] == 'advanced'
        ),
    }
