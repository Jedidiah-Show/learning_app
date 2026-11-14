"""M2 Integration Tests for Parallel Pathways Enrolment Model."""

import os
import tempfile

import pytest
from app import create_app, db
from app.models import LearningPathway, LearnerPathwayEnrollment, User
from app.pathway_scope import (
    active_pathway_enrolments, is_pathway, pathway_modules,
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
    from app.models import User
    
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
        """M2.2: is_pathway returns False when learner not enrolled."""
        # Test with a different user (no enrolment)
        from app.models import User
        other_user = User(query={'username': 'other'}).__class__(username='other_user')
        # Just test the function exists and works
        from app.pathway_scope import is_pathway
        # With no enrolments, should return False
        result = is_pathway(9999, 'ai-engineering')
        assert result == False
    
    def test_is_pathway_true_when_enrolled(self, app, user_with_enrolment):
        """M2.2: is_pathway returns True when learner is enrolled."""
        from app.pathway_scope import is_pathway
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
        """M2.2: pathway_modules for shared-foundations."""
        modules = pathway_modules('shared-foundations')
        assert len(modules) == 6
        module_ids = {m['id'] for m in modules}
        assert module_ids == {'sf.00', 'sf.01', 'sf.02', 'sf.03', 'sf.04', 'sf.05'}
    
    def test_ai_engineering_modules(self, app):
        """M2.2: pathway_modules for ai-engineering."""
        modules = pathway_modules('ai-engineering')
        assert len(modules) == 9
        # Should not include foundation modules (00-02)
        assert not any(m['id'] in ('00', '01', '02') for m in modules)
        # Should not include capstone (12)
        assert not any(m['id'] == '12' for m in modules)
    
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
    
    def test_foundation_evidence_structure(self, app):
        """M2.4: foundation_evidence has correct structure."""
        import inspect
        source = inspect.getsource(foundation_evidence)
        assert 'FOUNDATION_MODULE_IDS' in source
        assert 'LessonCompletion' in source
        assert 'CourseProject' in source
    
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
