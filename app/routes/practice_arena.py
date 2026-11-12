"""Routes for the RUACH Practice Arena.

Mounted at ``/arena`` so the existing lesson practice library can keep
``/practice`` (see ``app.routes.main.practice_catalog``).
"""

import json
import time

from flask import (
    Blueprint, Response, abort, current_app, jsonify, render_template, request, url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import PracticeWorkspace, Submission, utcnow
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
from app.services.judge import (
    _validate_code_syntax,
    execute_in_sandbox,
    validate_problem_schema,
)


practice_arena_bp = Blueprint(
    'practice_arena', __name__, url_prefix='/arena',
)

MAX_ARENA_SOURCE_LENGTH = 20000
PAGE_SIZE = 24


def _judge_submissions_enabled():
    """Prevent a production queue from accepting work with no safe executor."""
    return bool(
        current_app.testing
        or current_app.config.get('JUDGE_SUBMISSIONS_ENABLED', False)
    )


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


@practice_arena_bp.route('/machine-learning')
@login_required
def machine_learning():
    return _render_track('machine-learning')


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


@practice_arena_bp.route('/api/problems/<problem_id>/hint')
@login_required
def problem_hint(problem_id):
    raw = get_arena_problem(problem_id)
    if raw is None:
        return jsonify({'error': 'Problem not found'}), 404
    stage = request.args.get('stage', type=int)
    if stage is None or not 1 <= stage <= 5:
        return jsonify({'error': 'Hint stage must be between 1 and 5'}), 400
    enforce_rate_limit('arena-hint', str(current_user.id))
    workspace = _workspace_for(problem_id)
    if stage == 5 and workspace is None:
        return jsonify({
            'error': 'Save an attempt before revealing the editorial',
        }), 403
    latest = Submission.query.filter_by(
        user_id=current_user.id, problem_id=problem_id,
    ).order_by(Submission.submitted_at.desc()).first()
    from app.services.tutor import (
        assemble_tutor_context,
        diagnose_knowledge_gaps,
        generate_hint_stage,
    )
    context = assemble_tutor_context(
        current_user.id,
        problem_id=problem_id,
        code=workspace.source if workspace else '',
        error_log=latest.error_details if latest else None,
    )
    return jsonify({
        'stage': stage,
        'hint': generate_hint_stage(stage, context),
        'diagnosis': diagnose_knowledge_gaps(context),
    })


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


@practice_arena_bp.route('/api/problems/<problem_id>/submit', methods=['POST'])
@login_required
def submit_problem(problem_id):
    """Submit code for authoritative server-side judging.

    This endpoint replaces client-side Pyodide checks with an isolated
    containerized execution engine. Hidden test cases are never exposed
    to the client. Upon ACCEPTED verdict, associated skill competency
    is updated in the learner's Skill Passport.
    """
    raw = get_arena_problem(problem_id)
    if raw is None:
        return jsonify({'error': 'Problem not found'}), 404
    if not _judge_submissions_enabled():
        return jsonify({
            'error': (
                'Authoritative submissions are temporarily unavailable. '
                'Practice runs remain available in your browser.'
            ),
        }), 503
    if not raw.get('judge_tests'):
        return jsonify({
            'error': (
                'Verified grading is not available for this exercise yet. '
                'Use the browser checks to practise.'
            ),
        }), 409
    enforce_rate_limit('arena-submit', str(current_user.id))

    # Validate the problem schema before execution
    try:
        validate_problem_schema(raw)
    except ValueError as error:
        return jsonify({'error': str(error)}), 400

    if request.content_length is not None and request.content_length > MAX_ARENA_SOURCE_LENGTH + 1024:
        return jsonify({'error': 'Code is too large'}), 413
    data = get_json_object()
    if not isinstance(data, dict) or 'code' not in data:
        return jsonify({'error': 'Code is required in request body'}), 400

    code = data['code']
    if not isinstance(code, str) or not code.strip():
        return jsonify({'error': 'Code must be non-empty text'}), 400
    if len(code) > MAX_ARENA_SOURCE_LENGTH:
        return jsonify({'error': 'Code is too large'}), 413

    # Validate code syntax before sending to sandbox
    try:
        _validate_code_syntax(code)
    except ValueError as error:
        return jsonify({'error': str(error)}), 400

    # Persist first. A dedicated worker claims and executes this durable job.
    from uuid import uuid4
    submission_id = uuid4().hex

    submission = Submission(
        id=submission_id,
        user_id=current_user.id,
        problem_id=problem_id,
        language='python',
        code_snapshot=code,
        verdict='PENDING',
        submitted_at=utcnow(),
    )
    db.session.add(submission)
    db.session.commit()

    return jsonify({
        'submission_id': submission_id,
        'verdict': submission.verdict,
        'status': 'queued',
    }), 202

@practice_arena_bp.route('/api/problems/<problem_id>/run', methods=['POST'])
@login_required
def run_problem(problem_id):
    """Run learner code in the isolated sandbox for interactive feedback.

    Uses the same containerized execution engine as authoritative judging
    (``mode="run"``) but skips the private test suite and returns captured
    output instead of a verdict. Clients use this as the fast-path run
    mechanism and fall back to the in-browser runtime when it is unavailable.
    """
    raw = get_arena_problem(problem_id)
    if raw is None:
        return jsonify({'error': 'Problem not found'}), 404
    if not _judge_submissions_enabled():
        return jsonify({
            'error': (
                'Interactive server runs are temporarily unavailable. '
                'The in-browser runtime will be used instead.'
            ),
        }), 503
    if request.content_length is not None and request.content_length > MAX_ARENA_SOURCE_LENGTH + 1024:
        return jsonify({'error': 'Code is too large'}), 413
    data = get_json_object()
    if not isinstance(data, dict) or 'code' not in data:
        return jsonify({'error': 'Code is required in request body'}), 400
    code = data['code']
    if not isinstance(code, str) or not code.strip():
        return jsonify({'error': 'Code must be non-empty text'}), 400
    if len(code) > MAX_ARENA_SOURCE_LENGTH:
        return jsonify({'error': 'Code is too large'}), 413

    try:
        _validate_code_syntax(code)
    except ValueError as error:
        return jsonify({'error': str(error)}), 400

    enforce_rate_limit('arena-run', str(current_user.id))

    if data.get('async') or data.get('stream'):
        from uuid import uuid4
        run_id = uuid4().hex
        submission = Submission(
            id=run_id,
            user_id=current_user.id,
            problem_id=problem_id,
            language='python',
            code_snapshot=code,
            mode='run',
            verdict='PENDING',
            submitted_at=utcnow(),
        )
        db.session.add(submission)
        db.session.commit()
        return jsonify({
            'run_id': run_id,
            'status': 'queued',
            'stream_url': url_for('practice_arena.stream_execution', run_id=run_id),
        }), 202

    result = execute_in_sandbox(
        code,
        '',
        timeout_sec=15.0,
        memory_mb=512,
        mode='run',
    )
    if result.verdict == 'INTERNAL_ERROR' and 'unavailable' in (result.error_details or '').lower():
        return jsonify({
            'error': (
                'Interactive server runs are temporarily unavailable. '
                'The in-browser runtime will be used instead.'
            ),
        }), 503
    return jsonify({
        'verdict': result.verdict,
        'output': result.output,
        'error_details': result.error_details,
        'execution_time_ms': result.execution_time_ms,
        'memory_kb': result.memory_kb,
    })


@practice_arena_bp.route('/api/runs/<run_id>/stream')
@practice_arena_bp.route('/api/submissions/<run_id>/stream')
@login_required
def stream_execution(run_id):
    """Server-Sent Events (SSE) streaming endpoint for asynchronous runs and submissions."""
    submission = db.session.get(Submission, run_id)
    if submission is None:
        abort(404)
    if submission.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403

    app = current_app._get_current_object()

    def generate():
        with app.app_context():
            last_verdict = None
            start_time = time.monotonic()
            while time.monotonic() - start_time < 30.0:
                sub = db.session.get(Submission, run_id)
                if sub is None:
                    break
                if sub.verdict != last_verdict:
                    last_verdict = sub.verdict
                    payload = {
                        'run_id': sub.id,
                        'verdict': sub.verdict,
                        'output': sub.output or '',
                        'error_details': sub.error_details or '',
                        'execution_time_ms': sub.execution_time_ms,
                        'memory_kb': sub.memory_kb,
                        'tests_passed': sub.tests_passed,
                        'total_tests': sub.total_tests,
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                    if sub.verdict not in ('PENDING', 'RUNNING'):
                        break
                db.session.expire(sub)
                time.sleep(0.1)

    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache, no-transform'
    response.headers['X-Accel-Buffering'] = 'no'
    return response


@practice_arena_bp.route('/api/submissions/<submission_id>')
@login_required
def submission_status(submission_id):
    """Fetch verdict, run time, memory, and test results for a submission."""
    submission = db.session.get(Submission, submission_id)
    if submission is None:
        abort(404)

    # Ensure the learner can only view their own submissions
    if submission.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403

    return jsonify({
        'submission_id': submission.id,
        'verdict': submission.verdict,
        'execution_time_ms': submission.execution_time_ms,
        'memory_kb': submission.memory_kb,
        'tests_passed': submission.tests_passed,
        'total_tests': submission.total_tests,
        'error_details': submission.error_details,
        'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
    })
