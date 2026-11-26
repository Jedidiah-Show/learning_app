"""AI Engineering and Machine Learning must stay functionally independent."""

import pytest

from app import db
from app.ml_pathway import PATHWAY_ID
from app.models import (
    CourseProject,
    LessonCompletion,
    MLSpecializationLessonCompletion,
    MLSpecializationProject,
)
from app.pathway_scope import (
    _completion_state,
    active_pathway_enrolments,
    course_modules,
    enrol_learner_in_all,
    is_pathway,
    switch_pathway,
)


pytestmark = pytest.mark.regression


def test_both_specialisations_can_be_enrolled_and_switched(regression_app, learner):
    with regression_app.app_context():
        enrol_learner_in_all(learner, ('ai-engineering', 'machine-learning'))
        assert is_pathway(learner, 'ai-engineering') is True
        assert is_pathway(learner, 'machine-learning') is True
        assert len(active_pathway_enrolments(learner)) == 2

        assert switch_pathway(learner, 'machine-learning') == 'machine-learning'
        assert is_pathway(learner, 'ai-engineering') is True
        assert is_pathway(learner, 'machine-learning') is True


def test_completion_evidence_never_crosses_pathways(regression_app, learner):
    with regression_app.app_context():
        enrol_learner_in_all(learner, ('ai-engineering', 'machine-learning'))
        db.session.add(LessonCompletion(
            user_id=learner, lesson_id='0.01', subject_id='00', day_number=1,
            completed=True,
        ))
        db.session.add(CourseProject(
            user_id=learner, module_id='00', project='{}', completed=True,
        ))
        db.session.add(MLSpecializationLessonCompletion(
            user_id=learner, pathway_id=PATHWAY_ID, lesson_id='mle.tools.01',
        ))
        db.session.add(MLSpecializationProject(
            user_id=learner, pathway_id=PATHWAY_ID, module_id='mle.ai-tools',
            completed=True,
        ))
        db.session.commit()

        ai_lessons, ai_projects = _completion_state(learner, 'ai-engineering')
        ml_lessons, ml_projects = _completion_state(learner, 'machine-learning')
        assert '0.01' in ai_lessons and '0.01' not in ml_lessons
        assert 'mle.tools.01' in ml_lessons and 'mle.tools.01' not in ai_lessons
        assert '00' in ai_projects and 'mle.ai-tools' not in ai_projects
        assert 'mle.ai-tools' in ml_projects and '00' not in ml_projects

        ml_modules = {
            module['id']: module for module in course_modules('machine-learning', learner)
        }
        assert ml_modules['mle.ai-tools']['_completed_lessons'] == 1
        # Shared-foundation evidence is reusable, but it must not inflate the
        # AI specialisation's own module counts with an ML lesson.
        ai_modules = {
            module['id']: module for module in course_modules('ai-engineering', learner)
        }
        assert all(
            module['_completed_lessons'] == 0 for module in ai_modules.values()
        )
