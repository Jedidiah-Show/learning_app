"""Skill Passport Engine - maps curriculum lessons and practice problems
to competency nodes and tracks learner progress."""

from typing import Set, Dict, Any, Optional

from app import db
from app.models import SkillNode, UserSkillProgress, Submission, utcnow

CURRICULUM_SKILLS = {
    f'curriculum-{index:02d}': {
        'title': f'Module {index:02d} competencies',
        'category': 'curriculum',
    }
    for index in range(13)
}

PROJECT_SKILLS = {
    'production-rag': {
        'document-ingestion', 'permission-aware-retrieval', 'source-citations',
        'rag-evaluation',
    },
    'multi-tool-agent-mcp': {
        'tool-schema-design', 'bounded-agent-workflows', 'approval-checkpoints',
        'mcp-integration',
    },
    'evaluation-harness': {
        'llm-evaluation', 'golden-datasets', 'regression-testing',
    },
    'observable-microservice': {
        'service-observability', 'rate-limiting', 'container-deployment',
    },
    'validated-rest-api': {
        'api-design', 'request-validation', 'persistent-storage',
        'rate-limiting', 'api-testing',
    },
    'rag-document-retriever': {
        'document-ingestion', 'retrieval-ranking', 'rag-evaluation',
        'source-citations',
    },
}

ML_COMPETENCIES = {
    'ml-mathematics-statistics': {
        'title': 'Mathematics and statistics',
        'category': 'Machine Learning',
    },
    'ml-python-programming': {
        'title': 'Python programming',
        'category': 'Machine Learning',
    },
    'ml-data-analysis': {
        'title': 'Data analysis',
        'category': 'Machine Learning',
    },
    'ml-data-preparation': {
        'title': 'Data preparation',
        'category': 'Machine Learning',
    },
    'ml-feature-engineering': {
        'title': 'Feature engineering',
        'category': 'Machine Learning',
    },
    'ml-supervised-learning': {
        'title': 'Supervised learning',
        'category': 'Machine Learning',
    },
    'ml-unsupervised-learning': {
        'title': 'Unsupervised learning',
        'category': 'Machine Learning',
    },
    'ml-model-evaluation': {
        'title': 'Model evaluation',
        'category': 'Machine Learning',
    },
    'ml-deep-learning': {
        'title': 'Deep learning',
        'category': 'Machine Learning',
    },
    'ml-deployment': {
        'title': 'ML deployment',
        'category': 'Machine Learning',
    },
    'ml-mlops': {
        'title': 'MLOps',
        'category': 'Machine Learning',
    },
    'ml-responsible-ml': {
        'title': 'Responsible ML',
        'category': 'Machine Learning',
    },
}

ML_LESSON_COMPETENCIES = {
    'mle.math.01': {'ml-mathematics-statistics'},
    'mle.math.02': {'ml-mathematics-statistics'},
    'mle.math.03': {'ml-mathematics-statistics'},
    'mle.math.04': {'ml-mathematics-statistics'},
    'mle.math.05': {'ml-mathematics-statistics'},
    'mle.math.06': {'ml-mathematics-statistics'},
    'mle.math.07': {'ml-mathematics-statistics'},
    'mle.math.08': {'ml-mathematics-statistics'},
    'mle.data.01': {'ml-data-analysis', 'ml-model-evaluation', 'ml-responsible-ml'},
    'mle.data.02': {'ml-data-analysis', 'ml-data-preparation'},
    'mle.data.03': {'ml-data-preparation', 'ml-model-evaluation'},
    'mle.data.04': {
        'ml-data-preparation', 'ml-feature-engineering', 'ml-responsible-ml',
    },
    'mle.classical.01': {'ml-supervised-learning', 'ml-model-evaluation'},
    'mle.classical.02': {'ml-data-preparation', 'ml-supervised-learning'},
    'mle.classical.03': {'ml-model-evaluation'},
    'mle.classical.04': {'ml-model-evaluation'},
    'mle.repro.01': {'ml-mlops'},
    'mle.repro.02': {'ml-mlops'},
    'mle.repro.03': {'ml-mlops', 'ml-model-evaluation'},
    'mle.production.01': {'ml-deployment'},
    'mle.production.02': {'ml-deployment', 'ml-mlops', 'ml-responsible-ml'},
    'mle.production.03': {'ml-deployment', 'ml-mlops', 'ml-responsible-ml'},
    'mle.pytorch.01': {'ml-deep-learning', 'ml-supervised-learning'},
    'mle.pytorch.02': {'ml-deep-learning', 'ml-supervised-learning'},
    'mle.capstone.01': {
        'ml-python-programming', 'ml-data-analysis', 'ml-data-preparation',
        'ml-feature-engineering', 'ml-supervised-learning',
        'ml-model-evaluation', 'ml-deep-learning', 'ml-deployment', 'ml-mlops',
        'ml-responsible-ml',
    },
    'mle.capstone.02': {'ml-deployment', 'ml-mlops', 'ml-responsible-ml'},
}

ML_PROJECT_COMPETENCIES = {
    'mle.data-problem-formulation': {
        'ml-python-programming', 'ml-data-analysis', 'ml-data-preparation',
        'ml-feature-engineering', 'ml-responsible-ml',
    },
    'mle.classical-ml': {
        'ml-data-preparation', 'ml-supervised-learning', 'ml-model-evaluation',
    },
    'mle.reproducible-training': {'ml-mlops', 'ml-model-evaluation'},
    'mle.production-ml': {'ml-deployment', 'ml-mlops', 'ml-responsible-ml'},
    'mle.pytorch-advanced': {'ml-deep-learning', 'ml-supervised-learning'},
    'mle.capstone-integration': {
        'ml-python-programming', 'ml-data-analysis', 'ml-data-preparation',
        'ml-feature-engineering', 'ml-supervised-learning',
        'ml-model-evaluation', 'ml-deep-learning', 'ml-deployment', 'ml-mlops',
        'ml-responsible-ml',
    },
}


def _normalize_skill_name(name: str) -> str:
    """Normalize a skill name for consistent mapping."""
    import re

    return re.sub(r'[^a-z0-9-]+', '-', name.strip().lower()).strip('-')


def _normalized_title(skill_id: str, title: str) -> str:
    normalized_id = _normalize_skill_name(skill_id)[:64]
    normalized_name = _normalize_skill_name(title)[:63]
    return f'{normalized_id}-{normalized_name}'[:128]


def map_problem_skills(problem: dict, user_id: int) -> Set[str]:
    """Map a problem's skills to normalized skill names.

    Args:
        problem: Problem dict from arena problems data.
        user_id: User ID for querying existing progress.

    Returns:
        Set of normalized skill names from the problem.
    """
    skills = problem.get('skills', [])
    return {_normalize_skill_name(s) for s in skills if s}


def _ensure_skill_node(
    skill_id: str,
    category: Optional[str] = None,
    title: Optional[str] = None,
) -> None:
    if db.session.get(SkillNode, skill_id) is None:
        normalized_title = _normalized_title(
            skill_id, title or skill_id,
        )
        db.session.add(SkillNode(
            id=skill_id,
            title=title or skill_id.replace('-', ' ').replace('_', ' ').title(),
            normalized_title=normalized_title,
            category=category,
        ))


def _curriculum_lesson_nodes() -> Dict[str, Dict[str, str]]:
    from app.curriculum import all_modules

    nodes = {}
    for module in all_modules():
        for lesson in module.get('lessons', []):
            lesson_id = lesson.get('id')
            if not isinstance(lesson_id, str) or not lesson_id:
                continue
            normalized_id = _normalize_skill_name(
                lesson_id.replace('.', '-'),
            )
            nodes[f'lesson-{normalized_id}'] = {
                'title': lesson.get('title') or f'Lesson {lesson_id}',
                'category': 'curriculum',
            }
    return nodes


def ensure_all_skill_nodes() -> None:
    from app.practice_arena import all_arena_problems

    for skill_id, values in ML_COMPETENCIES.items():
        _ensure_skill_node(skill_id, values['category'], values['title'])
    for skill_id, values in CURRICULUM_SKILLS.items():
        if db.session.get(SkillNode, skill_id) is None:
            db.session.add(SkillNode(
                id=skill_id,
                title=values['title'],
                normalized_title=_normalized_title(skill_id, values['title']),
                category=values['category'],
            ))
    for skill_id, values in _curriculum_lesson_nodes().items():
        _ensure_skill_node(skill_id, values['category'], values['title'])
    for problem in all_arena_problems().values():
        for skill in map_problem_skills(problem, 0):
            _ensure_skill_node(skill, problem['track'])
    _ensure_skill_node('project-studio', 'projects')


# Evidence strength ordering: a stronger (more assessed) evidence type is
# never downgraded to a weaker one by an unrelated later verification.
EVIDENCE_RANK = {'LESSON': 1, 'PROBLEM': 2, 'LAB': 3, 'PROJECT': 4}


def _award_problem_skills(user_id, problem, evidence_type, *, commit=True):
    from app.practice_arena import all_arena_problems

    problem_id = problem['id']
    new_rank = EVIDENCE_RANK.get(evidence_type, 0)
    skills = map_problem_skills(problem, user_id)
    if not skills:
        return

    all_problems = all_arena_problems()
    for skill in skills:
        _ensure_skill_node(skill)
        # Use row-level lock to prevent race conditions on double submissions
        progress = UserSkillProgress.query.filter_by(
            user_id=user_id, skill_id=skill
        ).with_for_update().first()

        if progress is None:
            progress = UserSkillProgress(
                user_id=user_id,
                skill_id=skill,
                status='DEMONSTRATED',
                evidence_type=evidence_type,
                evidence_id=problem_id,
                updated_at=utcnow(),
            )
            db.session.add(progress)
        else:
            problem_ids = [
                candidate['id']
                for candidate in all_problems.values()
                if skill in map_problem_skills(candidate, user_id)
            ]
            accepted_count = Submission.query.filter(
                Submission.user_id == user_id,
                Submission.verdict == 'ACCEPTED',
                Submission.problem_id.in_(problem_ids),
            ).count()
            progress.status = (
                'MASTERED' if accepted_count >= 3 else 'DEMONSTRATED'
            )
            current_rank = EVIDENCE_RANK.get(progress.evidence_type or '', 0)
            if current_rank < new_rank:
                progress.evidence_type = evidence_type
                progress.evidence_id = problem_id
            progress.updated_at = utcnow()

    if commit:
        db.session.commit()


def update_skill_progress_from_submission(
    submission: Submission, *, commit: bool = True
) -> None:
    """Update UserSkillProgress when a submission is verified.

    If the submission was ACCEPTED, the associated skills are marked
    DEMONSTRATED (or MASTERED if the user has multiple accepted submissions
    on the same skill).

    Args:
        submission: The Submission record just verified by the judge.
    """
    from app.practice_arena import all_arena_problems

    # Only process ACCEPTED submissions
    if submission.verdict != 'ACCEPTED':
        return

    problem_id = submission.problem_id

    # Find the problem and its skills
    all_problems = all_arena_problems()
    problem = all_problems.get(problem_id)
    if problem is None:
        return

    _award_problem_skills(
        submission.user_id, problem, 'PROBLEM', commit=commit,
    )


def update_skill_progress_from_lab(
    user_id: int, lab_problem_id: str, *, commit: bool = True
) -> None:
    """Record lab-specific evidence when a learner passes the lab debrief.

    Labs assess more than the fix: the learner must diagnose the failure,
    justify the fix, and describe how they verified it. A passed debrief
    upgrades the lab problem's skills to LAB evidence.
    """
    from app.practice_arena import all_arena_problems

    problem = all_arena_problems().get(lab_problem_id)
    if problem is None or not problem.get('lab'):
        return

    _award_problem_skills(user_id, problem, 'LAB', commit=commit)


def update_skill_progress_from_project(
    user_id: int,
    project_id: str,
    project_skills: Optional[Set[str]] = None,
    *,
    commit: bool = True,
) -> None:
    """Update UserSkillProgress when a project is completed.

    Args:
        user_id: User ID.
        project_id: The project module ID (e.g., '01', '02', etc.).
        project_skills: Optional set of skill names demonstrated by the project.
    """
    skills = set(project_skills or ())
    skills.add('project-studio')
    for skill in skills:
        skill = _normalize_skill_name(skill)
        _ensure_skill_node(skill, 'projects')
        progress = UserSkillProgress.query.filter_by(
            user_id=user_id, skill_id=skill
        ).first()
        if progress is None:
            progress = UserSkillProgress(
                user_id=user_id,
                skill_id=skill,
                evidence_type='PROJECT',
                evidence_id=project_id,
                status='DEMONSTRATED',
                updated_at=utcnow(),
            )
            db.session.add(progress)
        else:
            progress.status = 'DEMONSTRATED'
            progress.evidence_type = 'PROJECT'
            progress.evidence_id = project_id
            progress.updated_at = utcnow()

    if commit:
        db.session.commit()


def update_skill_progress_from_lesson(
    user_id: int, lesson_id: str, *, commit: bool = True
) -> None:
    from app.practice_arena import topic_for_lesson
    from app.curriculum import get_lesson

    module_number = str(lesson_id).split('.', 1)[0]
    try:
        skill_id = f'curriculum-{int(module_number):02d}'
    except ValueError:
        skill_id = 'curriculum-00'
    topic_title = topic_for_lesson(lesson_id).replace('-', ' ').title()
    lesson = get_lesson(lesson_id) or {}
    lesson_skill_id = f'lesson-{_normalize_skill_name(lesson_id.replace(".", "-"))}'
    _ensure_skill_node(
        skill_id, 'curriculum', f'{topic_title} competencies',
    )
    _ensure_skill_node(
        lesson_skill_id,
        'curriculum',
        lesson.get('title') or f'Lesson {lesson_id}',
    )
    for competency_id in (skill_id, lesson_skill_id):
        progress = UserSkillProgress.query.filter_by(
            user_id=user_id, skill_id=competency_id,
        ).first()
        if progress is None:
            db.session.add(UserSkillProgress(
                user_id=user_id,
                skill_id=competency_id,
                status='DEVELOPING',
                evidence_type='LESSON',
                evidence_id=lesson_id,
                updated_at=utcnow(),
            ))
        elif progress.status == 'NOT_STARTED':
            progress.status = 'DEVELOPING'
            progress.evidence_type = 'LESSON'
            progress.evidence_id = lesson_id
    if commit:
        db.session.commit()


def update_skill_progress_from_ml_lesson(
    user_id: int, lesson_id: str, *, commit: bool = True
) -> None:
    """Record an ML lesson as developmental evidence, never verified mastery."""
    from app.ml_pathway import get_machine_learning_lesson

    lesson = get_machine_learning_lesson(lesson_id)
    if not lesson or lesson.get('status') != 'ready':
        return
    for skill_id in ML_LESSON_COMPETENCIES.get(lesson_id, ()):
        values = ML_COMPETENCIES[skill_id]
        _ensure_skill_node(skill_id, values['category'], values['title'])
        progress = UserSkillProgress.query.filter_by(
            user_id=user_id, skill_id=skill_id,
        ).with_for_update().first()
        if progress is None:
            db.session.add(UserSkillProgress(
                user_id=user_id,
                skill_id=skill_id,
                status='DEVELOPING',
                evidence_type='ML_LESSON',
                evidence_id=lesson_id,
                updated_at=utcnow(),
            ))
        elif progress.status not in {'DEMONSTRATED', 'MASTERED'}:
            progress.status = 'DEVELOPING'
            progress.evidence_type = 'ML_LESSON'
            progress.evidence_id = lesson_id
            progress.updated_at = utcnow()
    if commit:
        db.session.commit()


def reset_skill_progress_from_ml_project(
    user_id: int, module_id: str, *, commit: bool = True
) -> None:
    """Remove stale project evidence when a learner starts a new submission."""
    from app.models import MLSpecializationLessonCompletion
    from app.ml_pathway import PATHWAY_ID

    competencies = ML_PROJECT_COMPETENCIES.get(module_id, ())
    completed_lessons = {
        row.lesson_id for row in MLSpecializationLessonCompletion.query.filter_by(
            user_id=user_id, pathway_id=PATHWAY_ID,
        ).all()
    }
    for skill_id in competencies:
        progress = UserSkillProgress.query.filter_by(
            user_id=user_id,
            skill_id=skill_id,
            evidence_type='ML_PROJECT',
            evidence_id=module_id,
        ).with_for_update().first()
        if progress is None:
            continue
        lesson_evidence = next(
            (
                lesson_id for lesson_id, lesson_skills in ML_LESSON_COMPETENCIES.items()
                if skill_id in lesson_skills and lesson_id in completed_lessons
            ),
            None,
        )
        if lesson_evidence:
            progress.status = 'DEVELOPING'
            progress.evidence_type = 'ML_LESSON'
            progress.evidence_id = lesson_evidence
        else:
            progress.status = 'NOT_STARTED'
            progress.evidence_type = None
            progress.evidence_id = None
        progress.updated_at = utcnow()
    if commit:
        db.session.commit()


def update_skill_progress_from_ml_project(
    user_id: int, module_id: str, *, commit: bool = True
) -> None:
    """Record project evidence only after the ML project passes its checks."""
    from app.models import MLSpecializationProject
    from app.ml_pathway import PATHWAY_ID

    project = MLSpecializationProject.query.filter_by(
        user_id=user_id,
        pathway_id=PATHWAY_ID,
        module_id=module_id,
        completed=True,
    ).first()
    if project is None:
        return
    for skill_id in ML_PROJECT_COMPETENCIES.get(module_id, ()):
        values = ML_COMPETENCIES[skill_id]
        _ensure_skill_node(skill_id, values['category'], values['title'])
        progress = UserSkillProgress.query.filter_by(
            user_id=user_id, skill_id=skill_id,
        ).with_for_update().first()
        if progress is None:
            db.session.add(UserSkillProgress(
                user_id=user_id,
                skill_id=skill_id,
                status='DEMONSTRATED',
                evidence_type='ML_PROJECT',
                evidence_id=module_id,
                updated_at=utcnow(),
            ))
        else:
            progress.status = (
                'MASTERED' if progress.status == 'MASTERED' else 'DEMONSTRATED'
            )
            progress.evidence_type = 'ML_PROJECT'
            progress.evidence_id = module_id
            progress.updated_at = utcnow()
    if commit:
        db.session.commit()


def get_user_skill_state(user_id: int, skill_name: str) -> Optional[Dict[str, Any]]:
    """Get a user's current competency state for a specific skill.

    Returns dict with status and evidence, or None if no progress recorded.
    """
    progress = UserSkillProgress.query.filter_by(
        user_id=user_id, skill_id=skill_name
    ).first()

    if progress is None:
        return None

    return {
        'skill_id': progress.skill_id,
        'status': progress.status,
        'evidence_type': progress.evidence_type,
        'evidence_id': progress.evidence_id,
        'updated_at': progress.updated_at.isoformat() if progress.updated_at else None,
    }


def get_user_all_skill_states(user_id: int) -> Dict[str, Dict[str, Any]]:
    """Get all skill states for a user.

    Returns dict mapping skill_id to skill state dict without writing during
    reads. Lesson completions are projected as evidence if a legacy record has
    not yet been synchronized by the completion route.
    """
    from app.models import (
        LessonCompletion, MLSpecializationLessonCompletion,
        MLSpecializationProject,
    )
    from app.ml_pathway import PATHWAY_ID
    from app.practice_arena import all_arena_problems

    catalog = {
        skill_id: dict(values)
        for skill_id, values in CURRICULUM_SKILLS.items()
    }
    catalog.update({
        skill_id: dict(values)
        for skill_id, values in ML_COMPETENCIES.items()
    })
    catalog.update(_curriculum_lesson_nodes())
    for problem in all_arena_problems().values():
        for skill in map_problem_skills(problem, user_id):
            catalog.setdefault(skill, {
                'title': skill.replace('-', ' ').title(),
                'category': problem['track'],
            })
    catalog['project-studio'] = {
        'title': 'Project Studio competencies',
        'category': 'projects',
    }
    for skill_set in PROJECT_SKILLS.values():
        for skill in skill_set:
            catalog.setdefault(skill, {
                'title': skill.replace('-', ' ').title(),
                'category': 'projects',
            })
    for node in SkillNode.query.all():
        catalog[node.id] = {
            'title': node.title,
            'category': node.category,
        }

    states = {
        skill_id: {
            **values,
            'status': 'NOT_STARTED',
            'evidence_type': None,
            'evidence_id': None,
            'updated_at': None,
        }
        for skill_id, values in catalog.items()
    }
    for record in UserSkillProgress.query.filter_by(user_id=user_id).all():
        state = states.setdefault(record.skill_id, {
            'title': record.skill_id.replace('-', ' ').title(),
            'category': None,
        })
        state.update({
            'status': record.status or 'NOT_STARTED',
            'evidence_type': record.evidence_type,
            'evidence_id': record.evidence_id,
            'updated_at': record.updated_at.isoformat() if record.updated_at else None,
        })

    for completion in LessonCompletion.query.filter_by(
        user_id=user_id, completed=True,
    ).all():
        module_number = str(completion.lesson_id).split('.', 1)[0]
        try:
            module_skill_id = f'curriculum-{int(module_number):02d}'
        except ValueError:
            module_skill_id = 'curriculum-00'
        lesson_skill_id = (
            f'lesson-{_normalize_skill_name(completion.lesson_id.replace(".", "-"))}'
        )
        for skill_id in (module_skill_id, lesson_skill_id):
            state = states.get(skill_id)
            if state and state['status'] == 'NOT_STARTED':
                state.update({
                    'status': 'DEVELOPING',
                    'evidence_type': 'LESSON',
                    'evidence_id': completion.lesson_id,
                    'updated_at': (
                        completion.completed_at.isoformat()
                        if completion.completed_at else None
                    ),
                })

    for completion in MLSpecializationLessonCompletion.query.filter_by(
        user_id=user_id,
    ).all():
        for skill_id in ML_LESSON_COMPETENCIES.get(completion.lesson_id, ()):
            state = states.get(skill_id)
            if state and state['status'] == 'NOT_STARTED':
                state.update({
                    'status': 'DEVELOPING',
                    'evidence_type': 'ML_LESSON',
                    'evidence_id': completion.lesson_id,
                    'updated_at': (
                        completion.completed_at.isoformat()
                        if completion.completed_at else None
                    ),
                })

    for project in MLSpecializationProject.query.filter_by(
        user_id=user_id, pathway_id=PATHWAY_ID,
        completed=True,
    ).all():
        for skill_id in ML_PROJECT_COMPETENCIES.get(project.module_id, ()):
            state = states.get(skill_id)
            if state and state['status'] not in {'DEMONSTRATED', 'MASTERED'}:
                state.update({
                    'status': 'DEMONSTRATED',
                    'evidence_type': 'ML_PROJECT',
                    'evidence_id': project.module_id,
                    'updated_at': (
                        project.updated_at.isoformat()
                        if project.updated_at else None
                    ),
                })
    return states