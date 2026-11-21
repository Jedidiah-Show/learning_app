"""M1.5 — a lesson's curriculum record, not dashboard focus, scopes the tutor.

Regression coverage for the dual-enrolment bug: a learner who studies an AI
lesson while their dashboard is focused on ML (or vice versa) must receive the
syllabus and domain of the lesson in front of them. Dashboard focus remains a
display-only field in the prompt.
"""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from app import create_app, db
from app.domains.learning.context import (
    DOMAIN_AI_ENGINEERING,
    DOMAIN_MACHINE_LEARNING,
    DOMAIN_SHARED_FOUNDATIONS,
    ContextResolutionError,
    normalise_pathway,
    resolve_learning_context,
)
from app.models import (
    CoursePlan,
    LearnerPathwayEnrollment,
    LearningPathway,
    User,
)
from app.pathway_scope import seed_learning_pathways


# These are the ids the lesson API accepts. The resolver maps the bundled
# module prefix to the owning curriculum domain: 0/1/2 -> foundations,
# 3+ -> AI Engineering; the mle.* ids belong to Machine Learning.
AI_LESSON = '3.01'
ML_LESSON = 'mle.tools.01'
SF_LESSON = '0.01'

AI_MODULE_TITLE = 'LLM Fundamentals'
ML_MODULE_TITLE = 'AI Tools and Decision-Making'
SF_MODULE_TITLE = 'AI Engineering Foundations'


@pytest.fixture
def app():
    temp_dir = tempfile.TemporaryDirectory()
    previous_database_url = os.environ.get('DATABASE_URL')
    os.environ['DATABASE_URL'] = f'sqlite:///{temp_dir.name}/tutor-context.db'
    app = create_app()
    app.config.update(TESTING=True, GEMINI_API_KEY=None)
    with app.app_context():
        db.create_all()
        seed_learning_pathways()
    try:
        yield app
    finally:
        with app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        if previous_database_url is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = previous_database_url
        temp_dir.cleanup()


@pytest.fixture
def learner(app):
    client = app.test_client()
    response = client.post('/register', data={
        'username': 'contextlearner',
        'email': 'contextlearner@example.test',
        'password': 'secure-pass-123',
        'confirm_password': 'secure-pass-123',
        'full_name': 'Context Learner',
    }, follow_redirects=True)
    assert response.status_code == 200
    client.post('/onboarding', data={'action': 'skip'})
    with app.app_context():
        user = User.query.filter_by(username='contextlearner').one()
        return {'id': user.id, 'client': client}


def _set_focus_and_enrolments(app, user_id, focus, enrolments):
    """Write the dashboard focus and active enrolments directly."""
    with app.app_context():
        plan = CoursePlan.query.filter_by(user_id=user_id).first()
        if plan is None:
            plan = CoursePlan(user_id=user_id, track='standard')
            db.session.add(plan)
        plan.pathway_destination = focus
        seed_learning_pathways()
        LearnerPathwayEnrollment.query.filter_by(learner_id=user_id).delete()
        for pathway_id in enrolments:
            db.session.add(LearnerPathwayEnrollment(
                learner_id=user_id,
                pathway_id=pathway_id,
                status='ENROLLED',
            ))
        db.session.commit()
        assert LearningPathway.query.count() == 3
        assert {row.pathway_id for row in LearnerPathwayEnrollment.query.filter_by(
            learner_id=user_id
        )} == set(enrolments)


def _ask(client, lesson_id, *, explicit_context=None):
    """Send a tutor question and return the captured LLM prompt."""
    captured = {}

    def fake_generate_json(prompt, **kwargs):
        captured['prompt'] = prompt
        captured['kwargs'] = kwargs
        return {'in_scope': True, 'answer': 'In scope.', 'domain': 'unknown'}

    with patch('app.routes.lessons.lesson_is_available', return_value=True), \
         patch('app.routes.lessons.machine_learning_lesson_is_open', return_value=True), \
         patch('app.gemini.generate_json', side_effect=fake_generate_json):
        response = client.post('/api/lessons/ask', json={
            'lesson_id': lesson_id,
            'question': 'Why does this lesson use this approach?',
            'context': explicit_context,
        })
    assert response.status_code == 200, response.get_json()
    assert 'prompt' in captured, 'generate_json was not called'
    return captured['prompt'], response.get_json()


def _assert_prompt_scope(prompt, expected_pathway, display_focus, expected_title, other_title):
    assert f'Learner pathway: {expected_pathway}.' in prompt
    assert f'({expected_pathway})' in prompt
    assert f'Dashboard focus: {display_focus or "undecided"} (display only' in prompt
    assert json.dumps(expected_title) in prompt
    assert json.dumps(other_title) not in prompt


def _display_focus(app, user_id, focus):
    """The value destination_for() derives from plan + active enrolments."""
    if focus:
        return focus
    with app.app_context():
        from app.pathway_scope import destination_for
        return destination_for(user_id)


@pytest.mark.parametrize('lesson_id,focus,enrolments,expected,title,other_title', [
    (AI_LESSON, 'ai-engineering', ['ai-engineering'],
     DOMAIN_AI_ENGINEERING, AI_MODULE_TITLE, ML_MODULE_TITLE),
    (ML_LESSON, 'machine-learning', ['machine-learning'],
     DOMAIN_MACHINE_LEARNING, ML_MODULE_TITLE, AI_MODULE_TITLE),
    # The two mismatched-focus cases are the original bug.
    (AI_LESSON, 'machine-learning', ['ai-engineering', 'machine-learning'],
     DOMAIN_AI_ENGINEERING, AI_MODULE_TITLE, ML_MODULE_TITLE),
    (ML_LESSON, 'ai-engineering', ['ai-engineering', 'machine-learning'],
     DOMAIN_MACHINE_LEARNING, ML_MODULE_TITLE, AI_MODULE_TITLE),
    (SF_LESSON, 'machine-learning', ['shared-foundations', 'machine-learning'],
     DOMAIN_SHARED_FOUNDATIONS, SF_MODULE_TITLE, ML_MODULE_TITLE),
    (ML_LESSON, None, ['shared-foundations', 'machine-learning', 'ai-engineering'],
     DOMAIN_MACHINE_LEARNING, ML_MODULE_TITLE, AI_MODULE_TITLE),
])
def test_lesson_wins_over_dashboard_focus(
    app, learner, lesson_id, focus, enrolments, expected, title, other_title,
):
    _set_focus_and_enrolments(app, learner['id'], focus, enrolments)
    prompt, payload = _ask(learner['client'], lesson_id)

    display_focus = _display_focus(app, learner['id'], focus)
    _assert_prompt_scope(prompt, expected, display_focus, title, other_title)
    assert payload['in_scope'] is True
    assert payload['pathway_context']['active_pathway'] == expected
    assert payload['pathway_context']['dashboard_focus'] == display_focus


def test_switching_dashboard_focus_never_reassigns_a_lesson_pathway(app, learner):
    """A focus switch changes display state, never the lesson's syllabus."""
    _set_focus_and_enrolments(
        app, learner['id'], 'machine-learning',
        ['shared-foundations', 'ai-engineering', 'machine-learning'],
    )
    ai_prompt, ai_payload = _ask(learner['client'], AI_LESSON)
    _assert_prompt_scope(
        ai_prompt, DOMAIN_AI_ENGINEERING, 'machine-learning',
        AI_MODULE_TITLE, ML_MODULE_TITLE,
    )

    _set_focus_and_enrolments(
        app, learner['id'], 'ai-engineering',
        ['shared-foundations', 'ai-engineering', 'machine-learning'],
    )
    ml_prompt, ml_payload = _ask(learner['client'], ML_LESSON)
    _assert_prompt_scope(
        ml_prompt, DOMAIN_MACHINE_LEARNING, 'ai-engineering',
        ML_MODULE_TITLE, AI_MODULE_TITLE,
    )

    assert ai_payload['pathway_context']['active_pathway'] == DOMAIN_AI_ENGINEERING
    assert ml_payload['pathway_context']['active_pathway'] == DOMAIN_MACHINE_LEARNING


def test_conflicting_explicit_context_is_rejected(app, learner):
    _set_focus_and_enrolments(app, learner['id'], 'ai-engineering', ['ai-engineering'])
    with patch('app.gemini.generate_json') as generate_json:
        response = learner['client'].post('/api/lessons/ask', json={
            'lesson_id': ML_LESSON,
            'question': 'Can we switch this lesson to the AI syllabus?',
            'context': 'ai-engineering',
        })
    assert response.status_code == 400
    assert "conflicts with lesson pathway" in response.get_json()['error']
    generate_json.assert_not_called()


class TestLearningContextResolver:
    def test_normalise_pathway_handles_legacy_tokens(self):
        assert normalise_pathway('ml') == DOMAIN_MACHINE_LEARNING
        assert normalise_pathway('AI') == DOMAIN_AI_ENGINEERING
        assert normalise_pathway('shared') == DOMAIN_SHARED_FOUNDATIONS
        assert normalise_pathway('undecided') is None
        assert normalise_pathway('not-a-pathway') is None

    def test_lesson_domain_comes_from_the_curriculum_record(self):
        with pytest.raises(ContextResolutionError):
            resolve_learning_context(
                1, lesson_id=AI_LESSON, dashboard_focus='machine-learning',
                explicit_domain='machine-learning',
            )

    def test_dashboard_focus_is_only_a_fallback_without_a_lesson(self, app):
        with app.app_context():
            context = resolve_learning_context(
                1, dashboard_focus='machine-learning',
            )
        assert context.pathway_id == DOMAIN_MACHINE_LEARNING
        assert context.source == 'dashboard-focus'
        assert context.dashboard_focus == DOMAIN_MACHINE_LEARNING
