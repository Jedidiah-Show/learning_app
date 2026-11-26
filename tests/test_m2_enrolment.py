"""M2 Integration Tests for Parallel Pathways Enrolment Model."""

import os
import tempfile

import pytest
from app import create_app, db
from app.models import LearningPathway, LearnerPathwayEnrollment, User
from app.pathway_scope import (
    is_pathway, pathway_modules,
    pathway_lessons, foundation_evidence
)


@pytest.fixture
def app():
    """Create an isolated app instance backed by a temporary database."""
    temp_dir = tempfile.TemporaryDirectory()
    previous_database_url = os.environ.get('DATABASE_URL')
    os.environ['DATABASE_URL'] = f"sqlite:///{temp_dir.name}/test.db"
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db.create_all()
        from app.pathway_scope import seed_learning_pathways
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
def db_session(app):
    """Provide a transactional scope for a test."""
    with app.app_context():
        yield db.session


@pytest.fixture
def three_pathways(app, db_session):
    """Ensure three LearningPathway rows exist."""
    pathways = [
        LearningPathway(id='shared-foundations', slug='shared-foundations',
                        name='Shared Foundations', description='',
                        domain_type='FOUNDATION', version='1.0.0', status='ACTIVE'),
        LearningPathway(id='ai-engineering', slug='ai-engineering',
                        name='AI Engineering', description='',
                        domain_type='SPECIALIZATION', version='1.0.0', status='ACTIVE'),
        LearningPathway(id='machine-learning', slug='machine-learning',
                        name='Machine Learning', description='',
                        domain_type='SPECIALIZATION', version='1.0.0', status='ACTIVE'),
    ]
    for p in pathways:
        # Use merge to handle case where pathway already exists (test idempotency)
        db_session.merge(p)
    db_session.commit()
    
    # Ensure no enrolments exist
    LearnerPathwayEnrollment.query.delete()
    db_session.commit()
    
    return {'pathways': pathways, 'session': db_session}


@pytest.fixture
def user_with_enrolment(app, db_session):
    """Create a user with AI Engineering enrolment."""
    
    # Use unique credentials to avoid conflicts with existing test data
    import uuid
    unique_suffix = str(uuid.uuid4())[:8]
    email = f'testuser_{unique_suffix}@example.com'
    user = User(
        username=f'testuser_{unique_suffix}',
        email=email,
        full_name='Test User'
    )
    db_session.add(user)
    db_session.commit()
    
    # Enrol in AI Engineering
    enrolment = LearnerPathwayEnrollment(
        learner_id=user.id,
        pathway_id='ai-engineering',
        status='ENROLLED'
    )
    db_session.add(enrolment)
    db_session.commit()
    
    return {'user': user, 'session': db_session}


class TestPathwayEnrolmentModel:
    """Test the pathway enrolment model."""
    
    def test_three_pathways_exist(self, app, three_pathways):
        """M2.1: Three LearningPathway rows exist."""
        pathways = three_pathways['pathways']
        assert len(pathways) == 3
        pathway_ids = {p.id for p in pathways}
        assert pathway_ids == {'shared-foundations', 'ai-engineering', 'machine-learning'}
    
    def test_no_enrolments_initial(self, app, three_pathways):
        """M2.1: New user has no active enrolments."""
        enrolments = LearnerPathwayEnrollment.query.all()
        assert len(enrolments) == 0
    
    def test_is_pathway_false_when_no_enrolment(self, app, three_pathways, user_with_enrolment):
        """M2.2: an enrolled AI learner is not reported as enrolled in ML."""
        enrolled_id = user_with_enrolment['user'].id
        # The fixture's learner is enrolled in AI Engineering only, so the
        # other specialisation must read as not enrolled.
        assert is_pathway(enrolled_id, 'machine-learning') is False
    
    def test_is_pathway_true_when_enrolled(self, app, user_with_enrolment):
        """M2.2: is_pathway returns True when learner is enrolled."""
        user_id = user_with_enrolment['user'].id
        result = is_pathway(user_id, 'ai-engineering')
        assert result == True
        # Should not be true for ML when enrolled in AI
        result = is_pathway(user_id, 'machine-learning')
        assert result == False
    
    def test_active_pathway_ids(self, app, user_with_enrolment):
        """M2.2: active_pathway_ids returns correct set."""
        from app.pathway_scope import active_pathway_ids
        user_id = user_with_enrolment['user'].id
        ids = active_pathway_ids(user_id)
        assert ids == {'ai-engineering'}


class TestPathwayModules:
    """Test pathway_modules returns correct modules."""
    
    def test_shared_foundations_modules(self, app):
        """The foundations course has ONE canonical catalogue: six sf.* modules."""
        modules = pathway_modules('shared-foundations')
        assert len(modules) == 6
        module_ids = {m['id'] for m in modules}
        assert module_ids == {
            'sf.00', 'sf.01', 'sf.02', 'sf.03', 'sf.04', 'sf.05',
        }
        assert sum(len(m['lessons']) for m in modules) == 71
        assert all(len(m['lessons']) >= 3 for m in modules)

    def test_shared_foundations_course_view(self, app):
        """The foundations catalog counts only foundation lessons."""
        from app.pathway_scope import course_modules
        modules = course_modules('shared-foundations')
        assert [m['id'] for m in modules] == ['sf.00', 'sf.01', 'sf.02', 'sf.03', 'sf.04', 'sf.05']

    def test_undecided_catalog_is_the_foundation(self, app):
        """An undecided learner's catalog is the shared foundation only."""
        from app.pathway_scope import course_modules
        modules = course_modules(None)
        assert [m['id'] for m in modules] == ['sf.00', 'sf.01', 'sf.02', 'sf.03', 'sf.04', 'sf.05']

    def test_ai_engineering_modules(self, app):
        """The AI specialization is its own modules (03–12 incl. capstone)."""
        modules = pathway_modules('ai-engineering')
        assert len(modules) == 10
        # Should not include foundation modules (00-02)
        assert not any(m['id'] in ('00', '01', '02') for m in modules)
        # The capstone belongs to the AI pathway
        assert any(m['id'] == '12' for m in modules)
        # Foundations are a separate pathway, so AI modules are numbered 1..10
        # even though their stable legacy IDs remain 03..12.
        assert [m['number'] for m in modules] == list(range(1, 11))
    
    def test_ml_engineering_modules(self, app):
        """M2.2: pathway_modules for machine-learning."""
        modules = pathway_modules('machine-learning')
        assert len(modules) == 12


class TestPathwayLessons:
    """Test pathway_lessons returns lessons."""
    
    def test_shared_foundations_lessons(self, app):
        """M2.3: pathway_lessons for shared-foundations."""
        lessons = pathway_lessons('shared-foundations')
        assert len(lessons) > 0
    
    def test_ai_engineering_lessons(self, app):
        """M2.3: pathway_lessons for ai-engineering."""
        lessons = pathway_lessons('ai-engineering')
        assert len(lessons) > 0
    
    def test_ml_engineering_lessons(self, app):
        """M2.3: pathway_lessons for machine-learning."""
        lessons = pathway_lessons('machine-learning')
        assert len(lessons) > 0


class TestFoundationEvidence:
    """Test foundation evidence reuse."""
    
    def test_foundation_evidence_structure(self, app, db_session):
        """M2.4: foundation_evidence reads completion and project records.

        Behavioural check: seed the shared tables used by the helper and
        verify the evidence it reports, instead of asserting on source text.
        """
        from app.models import CourseProject, LessonCompletion
        from app.pathway_scope import foundation_modules

        user = User(username='evidence-user', email='evidence@example.test')
        db_session.add(user)
        db_session.commit()
        module = foundation_modules()[0]
        for lesson in module['lessons']:
            db_session.add(LessonCompletion(
                user_id=user.id, lesson_id=lesson['id'], subject_id=module['id'],
                day_number=1, completed=True,
            ))
        db_session.add(CourseProject(
            user_id=user.id, module_id=module['id'], project='{}', completed=True,
        ))
        db_session.commit()

        result = foundation_evidence(user.id)
        evidence = result[module['id']]
        assert evidence['completed_lessons'] == len(module['lessons'])
        assert evidence['completed_projects'] == 1
        assert evidence['complete'] is True
        assert evidence['ai_satisfied'] is False and evidence['ml_satisfied'] is False
        assert evidence['evidence_source'] == 'lesson_completion'
        assert set(result) == {
            item['id'] for item in foundation_modules()
        }
    
    def test_foundation_evidence_returns_dict(self, app, user_with_enrolment):
        """M2.4: foundation_evidence returns proper structure."""
        result = foundation_evidence(1)
        assert isinstance(result, dict)
        # Should have entries for all foundation modules
        assert len(result) == 6  # sf.00-sf.05


class TestCurriculumValidation:
    """Test curriculum validation results."""
    
    def test_no_module_id_overlap(self, app):
        """M1: No duplicate module IDs across curricula."""
        import json
        
        with open('shared_foundations_curriculum.json') as f:
            sf = json.load(f)
        with open('ai_engineering_curriculum.json') as f:
            ai = json.load(f)
        with open('machine_learning_curriculum.json') as f:
            ml = json.load(f)
        
        sf_ids = {m['id'] for m in sf['modules']}
        ai_ids = {m['id'] for m in ai['modules']}
        ml_ids = {m['id'] for m in ml['modules']}
        
        assert len(sf_ids & ai_ids) == 0
        assert len(sf_ids & ml_ids) == 0
        assert len(ai_ids & ml_ids) == 0


def test_destination_for_backward_compat(app, user_with_enrolment):
    """M2.1: destination_for backward-compatible alias."""
    from app.pathway_scope import destination_for
    
    # Should return the first enrolment's pathway_id (for the enrolled user)
    result = destination_for(user_with_enrolment['user'].id)
    assert result == 'ai-engineering'
    
    # With no enrolments (different user ID)
    result = destination_for(9999)
    assert result is None
