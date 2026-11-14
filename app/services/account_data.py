"""Inventory of everything a learner owns.

Account reset and account deletion used to delete a hand-maintained list of
tables, which silently drifted away from the schema: ML specialisation
progress, pathway choices, credentials, submissions, tutor history, community
posts, bookmarks, notes and support requests all survived a "reset".

This module keeps one registry of learner-owned models and applies an explicit
policy to each of them:

* ``DELETE``  - the rows are removed outright.
* ``TOMBSTONE`` - the content stays as a removed marker so other learners'
  threads keep their shape and the audit trail stays intact.
* ``RETAIN`` - the rows are kept on purpose, with the reason recorded here and
  surfaced in the learner-facing copy.

The registry is verified against the schema by
``tests/test_account_data.py`` so a new user-scoped table cannot be added
without deciding what happens to it.
"""

from datetime import datetime, timezone

from app import db
from app.models import (
    AIBackgroundJob, AdminAuditLog, CalendarEvent, CommunityPost,
    CommunityReply, CoursePlan, CourseProject, Credential, GeminiUsageBucket,
    LearningProject, LessonBookmark, LessonCompletion, LessonNote,
    LessonTaskProgress, MLSpecializationCredential,
    MLSpecializationLessonCompletion, MLSpecializationProject,
    MLProjectExperiment, PasswordResetToken, PathwayChangeRequest,
    PhoneVerificationCode, PracticeWorkspace, Progress, ProficiencyTest,
    QuizResult, ReviewItem, Submission, StudySession, SubjectCurriculum,
    SupportRequest, TutorConversation, User, UserConfig, UserProfilePhoto,
    UserSchedule, UserSkillProgress, UserSubject, UserSubjectConfig,
    VideoProgress,
)


# Rows removed completely when a learner resets or deletes their account.
DELETE_ON_RESET = (
    AIBackgroundJob,
    CalendarEvent,
    CoursePlan,
    CourseProject,
    Credential,
    LearningProject,
    LessonBookmark,
    LessonCompletion,
    LessonNote,
    LessonTaskProgress,
    MLSpecializationCredential,
    MLSpecializationLessonCompletion,
    MLSpecializationProject,
    MLProjectExperiment,
    PasswordResetToken,
    PathwayChangeRequest,
    PhoneVerificationCode,
    PracticeWorkspace,
    Progress,
    ProficiencyTest,
    QuizResult,
    ReviewItem,
    Submission,
    StudySession,
    SubjectCurriculum,
    SupportRequest,
    TutorConversation,
    UserConfig,
    UserProfilePhoto,
    UserSchedule,
    UserSkillProgress,
    UserSubject,
    UserSubjectConfig,
    VideoProgress,
)

# Rows kept as a visible tombstone instead of disappearing.
TOMBSTONE_ON_RESET = (
    CommunityPost,
    CommunityReply,
)

# Rows deliberately kept, with the reason shown to the learner.
RETAIN_ON_RESET = {
    GeminiUsageBucket: (
        'The shared AI usage bucket is preserved so a reset cannot be used to '
        'bypass the course quota.'
    ),
    AdminAuditLog: (
        'The administrator audit trail is retained for accountability.'
    ),
}

# Every learner-owned model in the schema, used by the drift test.
USER_OWNED_MODELS = tuple(
    sorted(
        set(DELETE_ON_RESET) | set(TOMBSTONE_ON_RESET) | set(RETAIN_ON_RESET),
        key=lambda model: model.__tablename__,
    )
)


def _utcnow():
    return datetime.now(timezone.utc)


def purge_user_data(user_id, session=None):
    """Apply the reset policy for one learner.

    Returns a summary dict with the number of rows removed per model and the
    models that were intentionally retained.
    """
    session = session or db.session
    removed = {}
    for model in DELETE_ON_RESET:
        count = session.query(model).filter(model.user_id == user_id).delete(
            synchronize_session=False,
        )
        if count:
            removed[model.__tablename__] = count
    for model in TOMBSTONE_ON_RESET:
        rows = session.query(model).filter(
            model.user_id == user_id, model.deleted_at.is_(None),
        ).all()
        for row in rows:
            row.deleted_at = _utcnow()
        if rows:
            removed[model.__tablename__] = len(rows)
    return {
        'removed': removed,
        'retained': {
            model.__tablename__: reason
            for model, reason in RETAIN_ON_RESET.items()
        },
    }


def reset_profile_counters(user, session=None):
    """Clear the streak counters that belong to the learner's progress."""
    session = session or db.session
    user.streak = 0
    user.longest_streak = 0
    user.last_study_date = None
    user.subjects_configured = False


def export_user_data(user_id, session=None):
    """Return everything the learner owns as a JSON-serialisable dict."""
    session = session or db.session
    export = {'generated_at': _utcnow().isoformat()}
    for model in USER_OWNED_MODELS:
        if model in RETAIN_ON_RESET:
            continue
        rows = session.query(model).filter(model.user_id == user_id).all()
        if not rows:
            continue
        export[model.__tablename__] = [_serialize(row) for row in rows]
    account = session.query(User).filter(User.id == user_id).one_or_none()
    if account is not None:
        export['account'] = {
            'username': account.username,
            'email': account.email,
            'full_name': account.full_name,
            'phone': account.phone,
            'phone_verified': account.phone_verified,
            'created_at': account.created_at.isoformat() if account.created_at else None,
            'streak': account.streak,
            'longest_streak': account.longest_streak,
        }
    return export


def _serialize(row):
    """Turn a model row into a JSON-friendly dict."""
    data = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif hasattr(value, 'isoformat'):
            value = value.isoformat()
        elif isinstance(value, bytes):
            value = f'<{len(value)} bytes>'
        data[column.name] = value
    return data
