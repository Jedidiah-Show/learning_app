"""Routes for the RUACH Practice Arena.

Mounted at ``/arena`` so the existing lesson practice library can keep
``/practice`` (see ``app.routes.main.practice_catalog``).
"""

from flask import (
    Blueprint, abort, current_app, jsonify, render_template, request, url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import PracticeWorkspace
from app.practice_arena import (
    TRACKS,
    all_arena_problems,
    catalogue,
    editorial_payload,
    get_arena_problem,
    problem_prerequisites,
    public_problem,
    sort_problems,
    stats_for_track,
    topic_by_id,
    track_by_id,
    track_topics,
)
from app.rate_limit import enforce_rate_limit
from app.request_data import get_json_object


practice_arena_bp = Blueprint(
    'practice_arena', __name__, url_prefix='/arena',
)

MAX_ARENA_SOURCE_LENGTH = 20000
PAGE_SIZE = 24


def _attempted_ids():
    rows = PracticeWorkspace.query.filter_by(user_id=current_user.id).all()
    return {row.exercise_id for row in rows}


def _latest_workspace():
    return (
        PracticeWorkspace.query
        .filter_by(user_id=current_user.id)
        .order_by(PracticeWorkspace.updated_at.desc())
        .first()
    )


def _status(item, attempted):
    attempted = item['id'] in attempted
    return {
        **item,
        'attempted': attempted,
        'status': 'practised' if attempted else 'not-started',
        'status_label': 'Practised' if attempted else 'Not started',
    }


def _decorate(problems, attempted):
    return [_status(problem, attempted) for problem in problems]


def _track_problems(track_id):
    return sort_problems(
        [
            problem for problem in all_arena_problems().values()
            if problem['track'] == track_id
        ],
        sort='recommended',
    )


def _track_stats(problems, track_id):
    stats = stats_for_track(problems, track_id)
    stats['topics'] = [
        {
            **topic,
            'count': sum(
                1 for problem in problems
                if problem['topic'] == topic['id']
            ),
        }
        for topic in track_topics(track_id)
    ]
    return stats


def _render_catalogue(track=None):
    result = catalogue(
        track=track,
        topic=request.args.get('topic'),
        difficulty=request.args.get('difficulty'),
        skill=request.args.get('skill'),
        query=request.args.get('q'),
        sort=request.args.get('sort', 'recommended'),
    )
    attempted = _attempted_ids()
    problems = _decorate(result['problems'], attempted)
    page = request.args.get('page', 1, type=int) or 1
    total = len(problems)
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(max(page, 1), pages)
    start = (page - 1) * PAGE_SIZE
    return {
        'problems': problems[start:start + PAGE_SIZE],
        'filters': result['filters'],
        'selected': result['selected'],
        'total': total,
        'page': page,
        'pages': pages,
    }


@practice_arena_bp.route('/')
@login_required
def index():
    problems = list(all_arena_problems().values())
    attempted = _attempted_ids()
    track_cards = []
    for track in TRACKS:
        track_cards.append({
            **track,
            **_track_stats(problems, track['id']),
        })
    latest = _latest_workspace()
    continue_problem = None
    if latest is not None:
        raw = get_arena_problem(latest.exercise_id)
        if raw is not None:
            continue_problem = _status(public_problem(raw), attempted)
    return render_template(
        'practice_arena/index.html',
        tracks=track_cards,
        continue_problem=continue_problem,
        total_problems=len(problems),
    )


@practice_arena_bp.route('/ai-engineering')
@login_required
def ai_engineering():
    return _render_track('ai-engineering')


@practice_arena_bp.route('/algorithms')
@login_required
def algorithms():
    return _render_track('algorithms')


def _render_track(track_id):
    track = track_by_id(track_id)
    if track is None:
        abort(404)
    problems = _track_problems(track_id)
    attempted = _attempted_ids()
    grouped = []
    for topic in track_topics(track_id):
        scoped = _decorate([
            problem for problem in problems if problem['topic'] == topic['id']
        ], attempted)
        if scoped:
            grouped.append({'topic': topic, 'problems': scoped})
    return render_template(
        'practice_arena/track.html',
        track=track,
        stats=_track_stats(problems, track_id),
        groups=grouped,
        total=len(problems),
    )


@practice_arena_bp.route('/problems')
@login_required
def problems():
    context = _render_catalogue(
        track=request.args.get('track') if request.args.get('track') else None,
    )
    return render_template('practice_arena/catalogue.html', **context)


@practice_arena_bp.route('/problems/<problem_id>')
@login_required
def problem_detail(problem_id):
    raw = get_arena_problem(problem_id)
    if raw is None:
        abort(404)
    attempted = _attempted_ids()
    problem = _status(public_problem(raw), attempted)
    siblings = _track_problems(problem['track'])
    position = next(
        (index for index, item in enumerate(siblings) if item['id'] == problem_id),
        None,
    )
    previous_problem = (
        public_problem(siblings[position - 1])
        if position is not None and position > 0 else None
    )
    next_problem = (
        public_problem(siblings[position + 1])
        if position is not None and position + 1 < len(siblings) else None
    )
    return render_template(
        'practice_arena/problem_detail.html',
        problem=problem,
        track=track_by_id(problem['track']),
        topic=topic_by_id(problem['topic']),
        prerequisites=[
            public_problem(item) for item in problem_prerequisites(raw)
        ],
        previous_problem=previous_problem,
        next_problem=next_problem,
    )


@practice_arena_bp.route('/api/problems')
@login_required
def api_problems():
    context = _render_catalogue(
        track=request.args.get('track') if request.args.get('track') else None,
    )
    return jsonify({
        'problems': context['problems'],
        'filters': context['filters'],
        'selected': context['selected'],
        'count': context['total'],
    })


@practice_arena_bp.route('/api/problems/<problem_id>')
@login_required
def api_problem(problem_id):
    raw = get_arena_problem(problem_id)
    if raw is None:
        return jsonify({'error': 'Problem not found'}), 404
    workspace = PracticeWorkspace.query.filter_by(
        user_id=current_user.id, exercise_id=problem_id,
    ).first()
    return jsonify({
        'problem': public_problem(raw),
        'source': (
            workspace.source if workspace else raw['starter_code']
        ),
        'updated_at': (
            workspace.updated_at.isoformat() if workspace else None
        ),
        'status': 'practised' if workspace else 'not-started',
    })


def _workspace_for(problem_id):
    return PracticeWorkspace.query.filter_by(
        user_id=current_user.id, exercise_id=problem_id,
    ).first()


@practice_arena_bp.route(
    '/api/problems/<problem_id>/workspace', methods=['PUT'],
)
@login_required
def save_workspace(problem_id):
    raw = get_arena_problem(problem_id)
    if raw is None:
        return jsonify({'error': 'Problem not found'}), 404
    if (
        request.content_length is not None
        and request.content_length > MAX_ARENA_SOURCE_LENGTH + 1024
    ):
        return jsonify({'error': 'Code is too large'}), 413
    data = get_json_object()
    source = data.get('source') if data else None
    if not isinstance(source, str):
        return jsonify({'error': 'Source must be text'}), 400
    if len(source) > MAX_ARENA_SOURCE_LENGTH:
        return jsonify({
            'error': (
                f'Code must be at most {MAX_ARENA_SOURCE_LENGTH} characters'
            ),
        }), 413
    workspace = _workspace_for(problem_id)
    if workspace is None:
        workspace = PracticeWorkspace(
            user_id=current_user.id, exercise_id=problem_id, source=source,
        )
        db.session.add(workspace)
    else:
        workspace.source = source
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        workspace = _workspace_for(problem_id)
        if workspace is None:
            raise
        workspace.source = source
        db.session.commit()
    return jsonify({
        'status': 'saved',
        'updated_at': workspace.updated_at.isoformat(),
    })


@practice_arena_bp.route('/api/problems/<problem_id>/editorial')
@login_required
def reveal_editorial(problem_id):
    raw = get_arena_problem(problem_id)
    if raw is None:
        return jsonify({'error': 'Problem not found'}), 404
    if not raw['solution_code'] and not raw['editorial']:
        return jsonify({'error': 'No editorial is available'}), 404
    if _workspace_for(problem_id) is None:
        return jsonify({
            'error': 'Save an attempt before revealing the worked solution',
        }), 403
    enforce_rate_limit('arena-editorial', str(current_user.id))
    payload = editorial_payload(raw)
    payload['notice'] = (
        'This worked solution is AI-authored course content, not an '
        'authoritative grade. Explain each decision in your own words.'
    )
    return jsonify(payload)


@practice_arena_bp.route('/api/tracks')
@login_required
def api_tracks():
    problems = list(all_arena_problems().values())
    return jsonify({
        'tracks': [
            {**track, **_track_stats(problems, track['id'])}
            for track in TRACKS
        ],
    })
