from app import db
from app.encrypted_types import EncryptedText
from datetime import datetime, date, timezone
from flask_login import UserMixin
import json


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(32), unique=True, nullable=True)
    username = db.Column(db.String(80), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(50), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    full_name = db.Column(db.String(120), nullable=True)
    profile_photo = db.Column(db.String(500), nullable=True)
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    google_access_token = db.Column(EncryptedText, nullable=True)
    google_refresh_token = db.Column(EncryptedText, nullable=True)
    token_expiry = db.Column(db.DateTime(timezone=True), nullable=True)
    auth_version = db.Column(
        db.Integer, nullable=False, default=0, server_default='0'
    )
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    last_active = db.Column(db.DateTime(timezone=True), default=utcnow)
    subjects_configured = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False, server_default='0')
    # Canonical role for authorization decisions (M4). is_admin is kept as a
    # synced compatibility flag: effective administrator == is_admin OR role
    # == 'administrator'. New grants/revocations must update both.
    role = db.Column(
        db.String(16), nullable=False, default='learner', server_default='learner'
    )
    # Overrides UserMixin.is_active so deactivated accounts cannot sign in and
    # active sessions are rejected by the user loader after the version bump.
    is_active = db.Column(
        db.Boolean, default=True, nullable=False, server_default='1'
    )
    streak = db.Column(db.Integer, default=0, nullable=False, server_default='0')
    longest_streak = db.Column(db.Integer, default=0, nullable=False, server_default='0')
    last_study_date = db.Column(db.Date)
    phone_verified = db.Column(
        db.Boolean, nullable=False, default=False, server_default=db.false()
    )
    
    progress = db.relationship('Progress', backref='user', lazy=True, cascade='all, delete-orphan')
    lesson_completions = db.relationship('LessonCompletion', backref='user', lazy=True, cascade='all, delete-orphan')
    quiz_results = db.relationship('QuizResult', backref='user', lazy=True, cascade='all, delete-orphan')
    study_sessions = db.relationship('StudySession', backref='user', lazy=True, cascade='all, delete-orphan')
    user_subject_configs = db.relationship('UserSubjectConfig', backref='user', lazy=True, cascade='all, delete-orphan')
    proficiency_tests = db.relationship('ProficiencyTest', backref='user', lazy=True, cascade='all, delete-orphan')
    calendar_events = db.relationship('CalendarEvent', backref='user', lazy=True, cascade='all, delete-orphan')
    user_subjects = db.relationship('UserSubject', backref='user', lazy=True, cascade='all, delete-orphan')
    user_schedule = db.relationship('UserSchedule', backref='user', lazy=True, cascade='all, delete-orphan', uselist=False)
    user_config = db.relationship('UserConfig', backref='user', lazy=True, cascade='all, delete-orphan', uselist=False)
    curricula = db.relationship('SubjectCurriculum', backref='user', lazy=True, cascade='all, delete-orphan')
    learning_projects = db.relationship('LearningProject', backref='user', lazy=True, cascade='all, delete-orphan')
    course_projects = db.relationship('CourseProject', backref='user', lazy=True, cascade='all, delete-orphan')
    password_reset_tokens = db.relationship(
        'PasswordResetToken', backref='user', lazy=True, cascade='all, delete-orphan'
    )
    gemini_usage_buckets = db.relationship(
        'GeminiUsageBucket', backref='user', lazy=True,
        cascade='all, delete-orphan',
    )
    ai_background_jobs = db.relationship(
        'AIBackgroundJob', backref='user', lazy=True,
        cascade='all, delete-orphan',
    )
    review_items = db.relationship(
        'ReviewItem', backref='user', lazy=True, cascade='all, delete-orphan',
    )
    video_progress = db.relationship(
        'VideoProgress', backref='user', lazy=True, cascade='all, delete-orphan',
    )
    practice_workspaces = db.relationship(
        'PracticeWorkspace', backref='user', lazy=True,
        cascade='all, delete-orphan',
    )
    lesson_bookmarks = db.relationship(
        'LessonBookmark', backref='user', lazy=True, cascade='all, delete-orphan',
    )
    lesson_notes = db.relationship(
        'LessonNote', backref='user', lazy=True, cascade='all, delete-orphan',
    )
    support_requests = db.relationship(
        'SupportRequest',
        backref='user',
        primaryjoin='SupportRequest.user_id == User.id',
        foreign_keys='SupportRequest.user_id',
        lazy=True,
        cascade='all, delete-orphan',
    )
    community_posts = db.relationship(
        'CommunityPost', backref='author', lazy=True, cascade='all, delete-orphan',
    )
    community_replies = db.relationship(
        'CommunityReply', backref='author', lazy=True, cascade='all, delete-orphan',
    )


class UserProfilePhoto(db.Model):
    """Durable profile photo bytes stored separately from frequently-read users."""
    __tablename__ = 'user_profile_photo'
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True
    )
    data = db.Column(db.LargeBinary, nullable=True)
    storage_key = db.Column(db.String(255), nullable=True)
    mime_type = db.Column(db.String(32), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    subject_id = db.Column(db.String(50), nullable=False)
    day_number = db.Column(db.Integer, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completion_date = db.Column(db.DateTime(timezone=True))
    time_spent_minutes = db.Column(db.Integer, default=0)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'subject_id', 'day_number', name='unique_user_subject_day'),
    )

class LessonCompletion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    lesson_id = db.Column(db.String(100), nullable=False)
    subject_id = db.Column(db.String(50), nullable=False)
    day_number = db.Column(db.Integer, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    started_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True))
    time_spent_minutes = db.Column(db.Integer, default=0)
    completion_source = db.Column(
        db.String(20), nullable=False, default='lesson',
        server_default='lesson',
    )
    __table_args__ = (
        db.UniqueConstraint('user_id', 'lesson_id', name='unique_user_lesson_completion'),
        db.Index('idx_lessoncomp_user_subject_day', 'user_id', 'subject_id', 'day_number'),
        db.Index('idx_lessoncomp_completed_user', 'completed', 'user_id'),
        db.Index('idx_lessoncomp_user_completed', 'user_id', 'completed'),
    )


class LessonTaskProgress(db.Model):
    """A learner's completion state for one task in a lesson."""
    __tablename__ = 'lesson_task_progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    lesson_id = db.Column(db.String(100), nullable=False)
    task_index = db.Column(db.Integer, nullable=False)
    completed = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
    __table_args__ = (
        db.UniqueConstraint(
            'user_id', 'lesson_id', 'task_index',
            name='unique_user_lesson_task_progress',
        ),
        db.Index('idx_lesson_task_progress_user_lesson', 'user_id', 'lesson_id'),
    )


class VideoProgress(db.Model):
    """Furthest watch position a learner has reported for a lesson video."""
    __tablename__ = 'video_progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    lesson_id = db.Column(db.String(100), nullable=False)
    video_id = db.Column(db.String(20), nullable=False)
    watched_seconds = db.Column(db.Integer, nullable=False, default=0)
    last_position = db.Column(db.Integer, nullable=False, default=0)
    duration_seconds = db.Column(db.Integer)
    completed = db.Column(
        db.Boolean, nullable=False, default=False, server_default=db.false()
    )
    completed_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    __table_args__ = (
        db.UniqueConstraint('user_id', 'lesson_id', name='unique_user_video_progress'),
        db.Index(
            'idx_videoprogress_user_completed', 'user_id', 'completed'
        ),
    )


class PracticeWorkspace(db.Model):
    """Saved source code for one learner's curated lesson exercise."""
    __tablename__ = 'practice_workspace'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    exercise_id = db.Column(db.String(100), nullable=False)
    source = db.Column(db.Text, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    __table_args__ = (
        db.UniqueConstraint(
            'user_id', 'exercise_id', name='unique_user_practice_workspace'
        ),
        db.Index('idx_practice_workspace_user', 'user_id'),
    )


class Submission(db.Model):
    """Authoritative server-side submission record with verdict.

    Stores code snapshots, execution metrics, and verdicts from the
    containerized judge engine. Each submission is tied to a user and
    problem, and tracks progress toward skill competency updates.
    """
    __tablename__ = 'submission'
    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    problem_id = db.Column(
        db.String(64), nullable=False
    )
    language = db.Column(db.String(32), default='python')
    code_snapshot = db.Column(db.Text, nullable=False)
    verdict = db.Column(
        db.Enum('PENDING', 'ACCEPTED', 'WRONG_ANSWER',
                'TIME_LIMIT_EXCEEDED', 'MEMORY_LIMIT_EXCEEDED',
                'RUNTIME_ERROR', 'COMPILE_ERROR', 'RUNNING',
                'INTERNAL_ERROR', 'COMPLETED', native_enum=False),
        default='PENDING', nullable=False
    )
    execution_time_ms = db.Column(db.Integer)
    memory_kb = db.Column(db.Integer)
    tests_passed = db.Column(db.Integer, default=0)
    total_tests = db.Column(db.Integer, default=0)
    error_details = db.Column(db.Text)
    output = db.Column(db.Text)
    mode = db.Column(db.String(16), default='judge')
    problem_version = db.Column(db.String(40), nullable=True)
    execution_profile = db.Column(
        db.String(40), nullable=True, index=True
    )
    submitted_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    started_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True))

    __table_args__ = (
        db.Index('idx_submission_user', 'user_id'),
        db.Index('idx_submission_user_submitted', 'user_id', 'submitted_at'),
        db.Index('idx_submission_problem', 'problem_id'),
        db.Index('idx_submission_verdict', 'verdict'),
        db.Index('idx_submission_queue', 'verdict', 'submitted_at'),
    )


class LabDebrief(db.Model):
    """A learner's diagnosis and verification write-up for an engineering lab.

    The judge owns correctness of the fix; this record captures the reasoning
    half of the lab: naming the root cause, explaining why the fix works, and
    describing how the fix was verified. The rubric scores the write-up; the
    judged verdict gates whether the lab counts as solved at all.
    """
    __tablename__ = 'lab_debrief'
    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    problem_id = db.Column(db.String(64), nullable=False)
    diagnosis = db.Column(db.Text, nullable=False)
    verification = db.Column(db.Text, nullable=False)
    score = db.Column(db.Integer)
    criterion_feedback = db.Column(db.Text)  # JSON list of {criterion, score, evidence, gap}
    evaluation_source = db.Column(
        db.String(16), nullable=False, default='local', server_default='local'
    )  # 'ai' or 'local'
    passed = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint('user_id', 'problem_id', name='unique_lab_debrief_user_problem'),
        db.Index('idx_lab_debrief_user', 'user_id'),
    )


class WorkspaceProject(db.Model):
    """A learner's multi-file project built in the browser workspace.

    Files are stored as a JSON object mapping path -> content and the whole
    set is written back in one request, so the server never holds partial
    editor state. The browser runs the project in Pyodide; the server only
    persists drafts.
    """
    __tablename__ = 'workspace_project'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    project_key = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    files = db.Column(db.Text, nullable=False, default='{}')
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint('user_id', 'project_key',
                            name='unique_workspace_project_user_key'),
        db.Index('idx_workspace_project_user', 'user_id'),
    )


class SkillNode(db.Model):
    """A competency node that maps to curriculum lessons, practice problems,
    or project studio milestones. User skill progress is tracked against
    these nodes.
    """
    __tablename__ = 'skill_node'
    id = db.Column(db.String(64), primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    normalized_title = db.Column(
        db.String(128), unique=True, nullable=False
    )  # lower-cased, stripped, used for consistent mapping
    category = db.Column(db.String(64)) # e.g., "Python", "RAG", "APIs"
    description = db.Column(db.Text)


class UserSkillProgress(db.Model):
    """Learner's progress toward demonstrating a specific competency node.

    Status evolves: NOT_STARTED -> DEVELOPING -> DEMONSTRATED -> MASTERED
    as evidence (problem submissions, project deliverables, lesson completions)
    is verified.
    """
    __tablename__ = 'user_skill_progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    skill_id = db.Column(
        db.String(64), db.ForeignKey('skill_node.id'), nullable=False
    )
    status = db.Column(
        db.Enum(
            'NOT_STARTED', 'DEVELOPING', 'DEMONSTRATED', 'MASTERED',
            native_enum=False,
        ),
        default='NOT_STARTED'
    )
    evidence_type = db.Column(db.String(32)) # "PROBLEM", "PROJECT", "LESSON", "LAB"
    evidence_id = db.Column(db.String(64)) # problem_id, project_id, or lesson_id
    verification_status = db.Column(
        db.String(24), nullable=False, server_default='UNVERIFIED'
    )
    verified_at = db.Column(db.DateTime(timezone=True), nullable=True)
    verified_by_user_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=True
    )
    verification_note = db.Column(db.Text)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    __table_args__ = (
        db.UniqueConstraint(
            'user_id', 'skill_id', name='unique_user_skill_progress',
        ),
        db.Index('idx_skillprogress_user', 'user_id'),
        db.Index('idx_skillprogress_skill', 'skill_id'),
        db.Index('idx_skillprogress_verification', 'verification_status'),
    )


class SkillVerification(db.Model):
    """Historical record of every verification transition for a competency.

    Preserved forever so evidence remains traceable across reassessment,
    invalidation, and revocation (G7 acceptance criteria).
    """
    __tablename__ = 'skill_verification'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    skill_id = db.Column(
        db.String(64), db.ForeignKey('skill_node.id'), nullable=False
    )
    from_status = db.Column(db.String(24))
    to_status = db.Column(db.String(24), nullable=False)
    requested_by_user_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=True
    )
    assessed_by_user_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=True
    )
    note = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, nullable=False
    )
    __table_args__ = (
        db.Index('idx_skillverification_user_skill', 'user_id', 'skill_id'),
        db.Index('idx_skillverification_created', 'created_at'),
    )


class PracticeUsageDaily(db.Model):
    """Daily pilot counters that intentionally contain no learner identifiers."""
    __tablename__ = 'practice_usage_daily'
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.Date, nullable=False)
    event = db.Column(db.String(20), nullable=False)
    count = db.Column(db.Integer, nullable=False, default=0)
    __table_args__ = (
        db.UniqueConstraint('day', 'event', name='unique_practice_usage_day_event'),
    )


class QuizResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    quiz_type = db.Column(db.String(20), nullable=False)  # 'daily', 'weekly'
    quiz_id = db.Column(db.String(100), nullable=False)
    subject_id = db.Column(db.String(50))
    day_number = db.Column(db.Integer)
    week_number = db.Column(db.Integer)
    score = db.Column(db.Integer)  # percentage
    total_questions = db.Column(db.Integer)
    correct_answers = db.Column(db.Integer)
    answers_data = db.Column(db.Text)  # JSON
    evaluation = db.Column(db.Text)
    attempt_id = db.Column(db.String(64))
    taken_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    passed = db.Column(db.Boolean, default=False)
    __table_args__ = (
        db.Index('idx_quizresult_quiz_id', 'quiz_id'),
        db.UniqueConstraint('user_id', 'quiz_id', 'attempt_id', name='unique_quiz_attempt'),
        db.Index('idx_quizresult_user_subject_day', 'user_id', 'subject_id', 'day_number'),
    )

class StudySession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    session_type = db.Column(db.String(20), nullable=False)  # 'morning', 'evening'
    date = db.Column(db.Date, default=date.today)
    start_time = db.Column(db.DateTime(timezone=True))
    end_time = db.Column(db.DateTime(timezone=True))
    duration_minutes = db.Column(db.Integer)
    subjects_studied = db.Column(db.Text)  # JSON list
    completed = db.Column(db.Boolean, default=False)
    __table_args__ = (
        db.Index('idx_studysession_user_date', 'user_id', 'date'),
    )

class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.String(100), unique=True, nullable=False)
    subject_id = db.Column(db.String(50), nullable=False)
    day_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)  # JSON
    objectives = db.Column(db.Text)
    difficulty = db.Column(db.Integer, default=1)
    estimated_minutes = db.Column(db.Integer, default=90)
    generated_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    is_ai_generated = db.Column(db.Boolean, default=False)
    __table_args__ = (
        db.Index('idx_lesson_subject_day', 'subject_id', 'day_number'),
    )
    
    def get_content(self):
        return json.loads(self.content) if self.content else {}
    
    def get_objectives(self):
        return json.loads(self.objectives) if self.objectives else []

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.String(100), unique=True, nullable=False)
    quiz_type = db.Column(db.String(20), nullable=False)  # 'daily', 'weekly'
    subject_id = db.Column(db.String(50))
    day_number = db.Column(db.Integer)
    week_number = db.Column(db.Integer)
    questions = db.Column(db.Text, nullable=False)  # JSON
    passing_threshold = db.Column(db.Integer, default=80)
    is_ai_generated = db.Column(db.Boolean, default=False, server_default=db.false(), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        db.Index('idx_quiz_type_day', 'quiz_type', 'day_number'),
        db.Index('idx_quiz_type_week', 'quiz_type', 'week_number'),
    )
    
    def get_questions(self):
        return json.loads(self.questions) if self.questions else []

class CalendarEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    event_id = db.Column(db.String(200), unique=True)  # Google Calendar event ID
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_time = db.Column(db.DateTime(timezone=True), nullable=False)
    end_time = db.Column(db.DateTime(timezone=True), nullable=False)
    subject_ids = db.Column(db.Text)  # JSON
    day_number = db.Column(db.Integer)
    block_name = db.Column(db.String(100))
    time_zone = db.Column(db.String(64))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    synced_to_google = db.Column(db.Boolean, default=False)
    sync_pending = db.Column(db.Boolean, default=False, nullable=False)
    delete_pending = db.Column(db.Boolean, default=False, nullable=False)
    google_sync_hash = db.Column(db.String(64))
    __table_args__ = (
        db.Index('idx_calendarevent_user', 'user_id'),
        db.Index('idx_calendarevent_user_day', 'user_id', 'day_number'),
        db.Index('idx_calendarevent_user_start', 'user_id', 'start_time'),
    )
    
    def get_subject_ids(self):
        return json.loads(self.subject_ids) if self.subject_ids else []


class UserSubjectConfig(db.Model):
    __tablename__ = 'user_subject_config'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    subject_id = db.Column(db.String(50), nullable=False)
    proficiency = db.Column(db.String(20), nullable=False)  # Novice through Expert
    tested = db.Column(db.Boolean, default=False)
    acquired_proficiency = db.Column(db.String(20))
    test_score = db.Column(db.Integer)
    configured_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'subject_id', name='unique_user_subject_config'),
    )


class UserSubject(db.Model):
    __tablename__ = 'user_subject'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    subject_id = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(10), default='📚')
    description = db.Column(db.Text)
    color = db.Column(db.String(20), default='#6366f1')
    priority = db.Column(db.Integer, default=1)
    topics = db.Column(db.Text)  # JSON list
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'subject_id', name='unique_user_custom_subject'),
    )

    def get_topics(self):
        return json.loads(self.topics) if self.topics else []

    def to_dict(self):
        return {
            'id': self.subject_id,
            'name': self.name,
            'icon': self.icon or '📚',
            'description': self.description or '',
            'color': self.color or '#6366f1',
            'priority': self.priority or 1,
            'topics': self.get_topics()
        }


class UserSchedule(db.Model):
    __tablename__ = 'user_schedule'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, unique=True)
    daily_blocks = db.Column(db.Text)  # JSON list of blocks
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def get_daily_blocks(self):
        return json.loads(self.daily_blocks) if self.daily_blocks else []


class UserConfig(db.Model):
    __tablename__ = 'user_config'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, unique=True)
    assessment_date = db.Column(db.String(20))  # YYYY-MM-DD
    extra_config = db.Column(db.Text)  # JSON for other overrides
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def get_extra_config(self):
        return json.loads(self.extra_config) if self.extra_config else {}


class ProficiencyTest(db.Model):
    __tablename__ = 'proficiency_test'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    subject_id = db.Column(db.String(50), nullable=False)
    questions = db.Column(db.Text, nullable=False)  # JSON
    answers_data = db.Column(db.Text)  # JSON
    evaluation = db.Column(db.Text)
    score = db.Column(db.Integer)
    source_signature = db.Column(db.String(64))
    is_ai_generated = db.Column(db.Boolean, default=False, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    taken_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        db.Index('idx_proftest_user_subject', 'user_id', 'subject_id'),
    )
    
    def get_questions(self):
        return json.loads(self.questions) if self.questions else []


class SubjectCurriculum(db.Model):
    __tablename__ = 'subject_curriculum'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    subject_id = db.Column(db.String(50), nullable=False)
    starting_proficiency = db.Column(db.String(20), nullable=False)
    source_signature = db.Column(db.String(64))
    plan = db.Column(db.Text, nullable=False)
    is_ai_generated = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'subject_id', name='unique_user_subject_curriculum'),
    )

    def get_plan(self):
        return json.loads(self.plan)


class LearningProject(db.Model):
    __tablename__ = 'learning_project'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    week_number = db.Column(db.Integer, nullable=False)
    project = db.Column(db.Text, nullable=False)
    submission = db.Column(db.Text)
    evaluation = db.Column(db.Text)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    is_ai_generated = db.Column(db.Boolean, default=False, nullable=False)
    source_signature = db.Column(db.String(64))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'week_number', name='unique_user_week_project'),
    )

    def get_project(self):
        return json.loads(self.project)

    def get_evaluation(self):
        return json.loads(self.evaluation) if self.evaluation else None


class CourseProject(db.Model):
    """Projects for the fixed RUACH course, isolated from legacy weekly projects."""
    __tablename__ = 'course_project'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    module_id = db.Column(db.String(10), nullable=False)
    project = db.Column(db.Text, nullable=False)
    is_ai_generated = db.Column(db.Boolean, default=False, server_default=db.false(), nullable=False)
    submission = db.Column(db.Text)
    repository_url = db.Column(db.String(500))
    commit_sha = db.Column(db.String(40))
    demo_url = db.Column(db.String(500))
    checks_url = db.Column(db.String(500))
    checks_verified = db.Column(
        db.Boolean, nullable=False, default=False, server_default=db.false()
    )
    evaluation = db.Column(db.Text)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'module_id', name='unique_user_course_module_project'),
        db.Index('idx_courseproject_completed_user', 'completed', 'user_id'),
    )

    def get_project(self):
        return json.loads(self.project) if self.project else {}

    def get_evaluation(self):
        return json.loads(self.evaluation) if self.evaluation else None


class MLSpecializationLessonCompletion(db.Model):
    """Completion records kept separate from the shared AI course lessons."""
    __tablename__ = 'ml_specialization_lesson_completion'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    pathway_id = db.Column(db.String(80), nullable=False)
    lesson_id = db.Column(db.String(100), nullable=False)
    completed_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (
        db.UniqueConstraint(
            'user_id', 'pathway_id', 'lesson_id',
            name='unique_user_ml_pathway_lesson',
        ),
        db.Index('idx_ml_lesson_user_pathway', 'user_id', 'pathway_id'),
    )


class MLSpecializationProject(db.Model):
    """Independent progress record for a specialization module project."""
    __tablename__ = 'ml_specialization_project'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    pathway_id = db.Column(db.String(80), nullable=False)
    module_id = db.Column(db.String(100), nullable=False)
    submission = db.Column(db.Text)
    evaluation = db.Column(db.Text)
    completed = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    # Stage B instrumentation: why the latest submission did not pass.
    # Server-owned taxonomy (see app.routes.ml_specialization), NULL when the
    # submission passed. Overwritten on each attempt, so the weekly snapshot
    # caveat in the pilot runbook applies to it too.
    failure_stage = db.Column(db.String(32))
    failure_detail = db.Column(db.String(300))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    __table_args__ = (
        db.UniqueConstraint(
            'user_id', 'pathway_id', 'module_id',
            name='unique_user_ml_pathway_project',
        ),
        db.Index('idx_ml_project_user_pathway', 'user_id', 'pathway_id'),
    )


class MLSpecializationCredential(db.Model):
    """Verifiable credential for the optional ML specialization."""
    __tablename__ = 'ml_specialization_credential'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    pathway_id = db.Column(db.String(80), nullable=False)
    public_id = db.Column(db.String(64), unique=True, nullable=False)
    recipient_name = db.Column(db.String(160), nullable=False)
    issued_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    revoked_at = db.Column(db.DateTime(timezone=True))
    __table_args__ = (
        db.UniqueConstraint(
            'user_id', 'pathway_id', name='unique_user_ml_pathway_credential'
        ),
        db.Index('idx_ml_credential_user', 'user_id'),
        db.Index('idx_ml_credential_public', 'public_id'),
    )


class MLProjectExperiment(db.Model):
    """Lightweight experiment log for ML specialization projects.

    Records one training/evaluation experiment so learners can document
    dataset version, preprocessing, model type, hyperparameters, and
    metrics — the core of experiment tracking (G9, Sprint 6).
    """

    __tablename__ = 'ml_project_experiment'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    pathway_id = db.Column(db.String(80), nullable=False)
    module_id = db.Column(db.String(100), nullable=False)
    experiment_name = db.Column(db.String(160), nullable=False)
    experiment_date = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    dataset_version = db.Column(db.String(120))
    preprocessing_approach = db.Column(db.Text)
    model_type = db.Column(db.String(120))
    hyperparameters = db.Column(db.Text)  # JSON string
    evaluation_metrics = db.Column(db.Text)  # JSON string
    observations = db.Column(db.Text)
    conclusion = db.Column(db.Text)
    # M3.8: MLflow identifiers are stored on the existing experiment record so
    # the LMS remains the source of truth and no duplicate experiment log is
    # introduced.
    mlflow_experiment_id = db.Column(db.String(80), nullable=True, index=True)
    mlflow_run_id = db.Column(db.String(80), nullable=True, index=True)
    tracking_uri = db.Column(db.String(500), nullable=True)
    run_status = db.Column(db.String(24), nullable=True)
    environment_json = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    __table_args__ = (
        db.Index('idx_ml_experiment_user_module', 'user_id', 'module_id'),
    )


class ProjectArtifact(db.Model):
    """Durable output created by a learner project or execution worker.

    Bytes live in the configured object-storage backend; PostgreSQL holds the
    authoritative metadata and authorization fields. ``project_type`` keeps
    course projects and ML specialization experiments separate without
    forcing a shared lifecycle on them.
    """

    __tablename__ = 'project_artifact'
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    project_type = db.Column(db.String(20), nullable=False)
    project_id = db.Column(db.Integer, nullable=True)
    artifact_type = db.Column(db.String(40), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    storage_key = db.Column(db.String(512), nullable=False, unique=True)
    size_bytes = db.Column(db.Integer, nullable=False)
    content_type = db.Column(db.String(120), nullable=False)
    checksum_sha256 = db.Column(db.String(64), nullable=False)
    access_policy = db.Column(
        db.String(20), nullable=False, default='private', server_default='private'
    )
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        db.Index(
            'idx_artifact_project', 'project_type', 'project_id', 'created_at'
        ),
        db.Index('idx_artifact_owner_created', 'owner_id', 'created_at'),
    )


class JudgeWorkerHeartbeat(db.Model):
    """Latest registration and health report from an execution worker."""

    __tablename__ = 'judge_worker_heartbeat'
    id = db.Column(db.String(80), primary_key=True)
    hostname = db.Column(db.String(120), nullable=False)
    pid = db.Column(db.Integer, nullable=False)
    status = db.Column(
        db.String(20), nullable=False, default='online', server_default='online'
    )
    execution_profiles = db.Column(db.Text)  # JSON list
    pending_count = db.Column(db.Integer, nullable=False, default=0)
    running_count = db.Column(db.Integer, nullable=False, default=0)
    processed_count = db.Column(db.Integer, nullable=False, default=0)
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class ServiceHeartbeat(db.Model):
    """Latest availability report from a non-web operational process (M5).

    The judge worker keeps its own specialised heartbeat; this generic row
    covers the AI worker, scheduler and any future compute worker without
    introducing a second queue or an external broker. ``detail_json`` holds
    metadata only — no learner content or credentials.
    """

    __tablename__ = 'service_heartbeat'
    service = db.Column(db.String(40), primary_key=True)
    instance_id = db.Column(db.String(120), nullable=False)
    status = db.Column(
        db.String(20), nullable=False, default='online', server_default='online'
    )
    detail_json = db.Column(db.Text)
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    last_seen_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )

    def get_detail(self):
        return json.loads(self.detail_json or '{}')


class CoursePlan(db.Model):
    """Learner-selected required capstone and independent portfolio project."""
    __tablename__ = 'course_plan'
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True
    )
    required_project_id = db.Column(db.String(50))
    portfolio_title = db.Column(db.String(160))
    portfolio_summary = db.Column(db.Text)
    portfolio_repository_url = db.Column(db.String(500))
    portfolio_demo_url = db.Column(db.String(500))
    showcase_visibility = db.Column(
        db.String(20), nullable=False, default='private', server_default='private'
    )
    leaderboard_opt_in = db.Column(
        db.Boolean, nullable=False, default=False, server_default=db.false()
    )
    track = db.Column(
        db.String(20), nullable=False, default='standard',
        server_default='standard',
    )
    # Prior knowledge and available time are separate answers; conflating them
    # made the pace recommendation assume that a beginner needs more months.
    skill_level = db.Column(db.String(32))
    weekly_hours = db.Column(db.Integer)
    setup_checks = db.Column(db.Text)
    # Stage D pathway destination: the fit assessment proposes ('ai', 'ml', or
    # 'undecided') and the learner explicitly confirms or overrides it. Both
    # are stored so the dashboard can lead with the confirmed choice while the
    # proposal stays available for later analysis. NULL means never assessed.
    pathway_proposal = db.Column(db.String(16))
    pathway_destination = db.Column(db.String(16))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    __table_args__ = (
        db.Index('idx_course_plan_leaderboard_opt_in', 'leaderboard_opt_in'),
    )



class LearningPathway(db.Model):
    """The three learning domains — Shared Foundations, AI Engineering, Machine Learning."""
    __tablename__ = 'learning_pathway'
    id = db.Column(db.String(80), primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    domain_type = db.Column(db.String(20), nullable=False)
    version = db.Column(db.String(16), nullable=False, server_default='1.0.0')
    status = db.Column(db.String(16), nullable=False, server_default='ACTIVE')
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

class LearnerPathwayEnrollment(db.Model):
    """A learner's enrolment in a learning pathway.

    A learner may have zero, one, or multiple active enrolments.  Each enrolment
    independently scopes the lesson catalog, progress calculations, and pacing.
    Pausing one enrolment does not affect the other; completing one does not
    automatically complete the other.
    """
    __tablename__ = 'learner_pathway_enrollment'
    id = db.Column(db.Integer, primary_key=True)
    learner_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    pathway_id = db.Column(
        db.String(80), db.ForeignKey('learning_pathway.id', ondelete='CASCADE'),
        nullable=False,
    )
    status = db.Column(
        db.String(20), nullable=False, server_default='ENROLLED')
    enrolled_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    paused_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    __table_args__ = (
        db.UniqueConstraint('learner_id', 'pathway_id',
                            name='unique_learner_pathway_enrollment'),
        db.Index('idx_enrolment_learner_status', 'learner_id', 'status'),
    )


class AISpecializationProject(db.Model):
    """Independent progress record for an AI Engineering module project.

    AI Engineering project records live in their own table and never share
    rows with Machine Learning project records; AI evidence cannot credit
    ML competencies and vice versa.
    """
    __tablename__ = 'ai_specialization_project'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    pathway_id = db.Column(db.String(80), nullable=False)
    module_id = db.Column(db.String(100), nullable=False)
    submission = db.Column(db.Text)
    evaluation = db.Column(db.Text)
    completed = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    failure_stage = db.Column(db.String(32))
    failure_detail = db.Column(db.String(300))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    __table_args__ = (
        db.UniqueConstraint(
            'user_id', 'pathway_id', 'module_id',
            name='unique_user_ai_pathway_project',
        ),
        db.Index('idx_ai_project_user_pathway', 'user_id', 'pathway_id'),
    )


class AIPromptVersion(db.Model):
    """Prompt versions for an AI Engineering project."""
    __tablename__ = 'ai_prompt_version'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    pathway_id = db.Column(db.String(80), nullable=False)
    module_id = db.Column(db.String(100), nullable=False)
    version = db.Column(db.Integer, nullable=False)
    prompt_content = db.Column(db.Text, nullable=False)
    model_configuration = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (
        db.UniqueConstraint(
            'user_id', 'pathway_id', 'module_id', 'version',
            name='unique_ai_prompt_version',
        ),
        db.Index('idx_ai_prompt_version_user_module', 'user_id', 'module_id'),
    )


class AIRetrievalConfiguration(db.Model):
    """Retrieval configurations for an AI Engineering project."""
    __tablename__ = 'ai_retrieval_configuration'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    pathway_id = db.Column(db.String(80), nullable=False)
    module_id = db.Column(db.String(100), nullable=False)
    chunking_configuration = db.Column(db.Text)  # JSON string
    embedding_configuration = db.Column(db.Text)  # JSON string
    retrieval_parameters = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (
        db.UniqueConstraint(
            'user_id', 'pathway_id', 'module_id',
            name='unique_ai_retrieval_configuration',
        ),
        db.Index('idx_ai_retrieval_config_user_module', 'user_id', 'module_id'),
    )


class AIAgentExecutionRecord(db.Model):
    """Agent execution traces for an AI Engineering project."""
    __tablename__ = 'ai_agent_execution_record'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    pathway_id = db.Column(db.String(80), nullable=False)
    module_id = db.Column(db.String(100), nullable=False)
    execution_id = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(32), nullable=False)
    tool_calls = db.Column(db.Text)  # JSON string
    duration = db.Column(db.Integer)  # milliseconds
    error_summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (
        db.Index('idx_ai_agent_execution_user_module', 'user_id', 'module_id'),
    )


class AIEvaluationRecord(db.Model):
    """Evaluation results for an AI Engineering project."""
    __tablename__ = 'ai_evaluation_record'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    pathway_id = db.Column(db.String(80), nullable=False)
    module_id = db.Column(db.String(100), nullable=False)
    evaluation_dataset = db.Column(db.String(200))
    evaluation_results = db.Column(db.Text)  # JSON string
    metric_summary = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (
        db.Index('idx_ai_evaluation_user_module', 'user_id', 'module_id'),
    )


class LeaderboardScore(db.Model):
    """Materialized learning totals used by the opt-in leaderboard."""
    __tablename__ = 'leaderboard_score'
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True
    )
    lessons = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    projects = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    ml_lessons = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    ml_projects = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    __table_args__ = (db.Index('idx_leaderboard_score_updated', 'updated_at'),)


class PathwayChangeRequest(db.Model):
    """A learner's single request to change a confirmed pathway.

    The destination is a hard lock after onboarding, so the only learner-facing
    route back out is one request, available once the shared foundation (modules
    00-02) is complete, and only an admin may resolve it. The row records both
    the requested and the resulting destination so the audit trail survives the
    change itself.
    """
    __tablename__ = 'pathway_change_request'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False,
        unique=True,
    )
    requested_destination = db.Column(db.String(16), nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(
        db.String(16), nullable=False, default='pending', server_default='pending'
    )
    resolved_by = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True
    )
    resolved_destination = db.Column(db.String(16))
    resolution_note = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
    resolved_at = db.Column(db.DateTime(timezone=True))
    __table_args__ = (
        db.Index('idx_pathway_change_request_user', 'user_id'),
        db.Index('idx_pathway_change_request_status', 'status'),
    )

    requester = db.relationship('User', foreign_keys=[user_id])
    resolver = db.relationship('User', foreign_keys=[resolved_by])

    @property
    def is_pending(self):
        return self.status == 'pending'


class Credential(db.Model):
    """Publicly verifiable record of completed course requirements."""
    __tablename__ = 'credential'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    public_id = db.Column(db.String(64), unique=True, nullable=False)
    course_title = db.Column(db.String(160), nullable=False)
    recipient_name = db.Column(db.String(160), nullable=False)
    issued_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    revoked_at = db.Column(db.DateTime(timezone=True))
    __table_args__ = (
        db.Index('idx_credential_user', 'user_id'),
    )


class CommunityPost(db.Model):
    __tablename__ = 'community_post'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    topic = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(140), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    replies = db.relationship(
        'CommunityReply', backref='post', lazy=True, cascade='all, delete-orphan',
        order_by='CommunityReply.created_at',
    )
    __table_args__ = (
        db.Index('idx_community_post_user', 'user_id'),
        db.Index('idx_community_post_updated', 'updated_at'),
        db.Index('idx_community_post_topic_updated', 'topic', 'updated_at'),
    )


class CommunityReply(db.Model):
    __tablename__ = 'community_reply'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(
        db.Integer, db.ForeignKey('community_post.id', ondelete='CASCADE'), nullable=False
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (
        db.Index('idx_community_reply_post_created', 'post_id', 'created_at'),
        db.Index('idx_community_reply_user', 'user_id'),
    )


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_token'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (
        db.Index('idx_password_reset_user', 'user_id'),
        db.Index('idx_password_reset_expiry', 'expires_at'),
    )


class RateLimitCounter(db.Model):
    """A fixed-window counter shared by all application instances."""
    __tablename__ = 'rate_limit_counter'
    id = db.Column(db.Integer, primary_key=True)
    bucket = db.Column(db.String(255), nullable=False)
    window_start = db.Column(db.DateTime(timezone=True), nullable=False)
    count = db.Column(db.Integer, nullable=False, default=0)
    __table_args__ = (
        db.UniqueConstraint(
            'bucket', 'window_start', name='uq_rate_limit_bucket_window'
        ),
        db.Index('idx_rate_limit_window', 'window_start'),
    )


class GeminiUsageBucket(db.Model):
    __tablename__ = 'gemini_usage_bucket'
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True
    )
    window = db.Column(db.String(10), primary_key=True)
    bucket_start = db.Column(db.DateTime(timezone=True), primary_key=True)
    request_count = db.Column(db.Integer, nullable=False, default=0)
    __table_args__ = (
        db.Index('idx_gemini_usage_user_bucket', 'user_id', 'bucket_start'),
    )


class AIBackgroundJob(db.Model):
    __tablename__ = 'ai_background_job'
    id = db.Column(db.Integer, primary_key=True)
    job_key = db.Column(db.String(160), unique=True, nullable=False)
    job_type = db.Column(db.String(40), nullable=False)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    payload = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='queued')
    attempts = db.Column(db.Integer, nullable=False, default=0)
    max_attempts = db.Column(db.Integer, nullable=False, default=3)
    available_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    locked_at = db.Column(db.DateTime(timezone=True))
    lease_token = db.Column(db.String(64))
    started_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True))
    progress_pct = db.Column(db.Integer, nullable=False, default=0)
    result_ref = db.Column(db.String(255))
    correlation_id = db.Column(db.String(64))
    cancelled_at = db.Column(db.DateTime(timezone=True))
    last_error = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
    __table_args__ = (
        db.Index('idx_ai_job_status_available', 'status', 'available_at'),
        db.Index('idx_ai_job_user', 'user_id'),
        db.Index('idx_ai_job_correlation', 'correlation_id'),
        db.Index('idx_ai_job_locked_at', 'locked_at'),
    )


class AIUsageRecord(db.Model):
    """Privacy-conscious telemetry for AI provider calls (M2.6/M2.8).

    Prompt and response bodies are deliberately not stored. Missing provider
    token counts remain ``None`` instead of being guessed.
    """

    __tablename__ = 'ai_usage_record'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(64), unique=True, nullable=False)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True
    )
    task_type = db.Column(db.String(40), nullable=False)
    provider = db.Column(db.String(20))
    model = db.Column(db.String(120))
    status = db.Column(db.String(20), nullable=False, default='success')
    input_tokens = db.Column(db.Integer)
    output_tokens = db.Column(db.Integer)
    estimated_cost_usd = db.Column(db.Float)
    duration_ms = db.Column(db.Integer, nullable=False, default=0)
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    prompt_version = db.Column(db.String(40))
    correlation_id = db.Column(db.String(64))
    error_code = db.Column(db.String(80))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (
        db.Index('idx_ai_usage_created', 'created_at'),
        db.Index('idx_ai_usage_task', 'task_type', 'created_at'),
        db.Index('idx_ai_usage_correlation', 'correlation_id'),
    )


class AIJobResult(db.Model):
    """Durable, bounded result reference for an AI background job (M2.4)."""

    __tablename__ = 'ai_job_result'
    job_id = db.Column(
        db.Integer,
        db.ForeignKey('ai_background_job.id', ondelete='CASCADE'),
        primary_key=True,
    )
    result_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class ReviewItem(db.Model):
    __tablename__ = 'review_item'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    quiz_id = db.Column(db.String(100), nullable=False)
    question_id = db.Column(db.String(100), nullable=False)
    subject_id = db.Column(db.String(50), nullable=False)
    question = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, nullable=False)
    correct_index = db.Column(db.Integer, nullable=False)
    explanation = db.Column(db.Text)
    due_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    interval_days = db.Column(db.Integer, nullable=False, default=1)
    repetitions = db.Column(db.Integer, nullable=False, default=0)
    active = db.Column(db.Boolean, nullable=False, default=True)
    # Nullable on purpose: shared-course review rows predate pathway routing
    # and stay NULL. Only namespaced pathway items carry a value.
    pathway_id = db.Column(db.String(80))
    __table_args__ = (
        db.UniqueConstraint(
            'user_id', 'quiz_id', 'question_id', name='unique_review_question'
        ),
        db.Index('idx_review_due', 'user_id', 'active', 'due_at'),
        db.Index('idx_review_user_pathway', 'user_id', 'pathway_id'),
    )

    def get_options(self):
        return json.loads(self.options) if self.options else []


class AdminAuditLog(db.Model):
    """Immutable trail of administrative changes for accountability."""
    __tablename__ = 'admin_audit_log'
    id = db.Column(db.Integer, primary_key=True)
    admin_user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True
    )
    action = db.Column(db.String(80), nullable=False)
    target_user_id = db.Column(db.Integer, nullable=True)
    detail = db.Column(db.Text)
    ip_address = db.Column(db.String(64))
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )
    __table_args__ = (
        db.Index('idx_admin_audit_admin', 'admin_user_id'),
        db.Index('idx_admin_audit_target', 'target_user_id'),
        db.Index('idx_admin_audit_action', 'action'),
    )

    admin = db.relationship('User', foreign_keys=[admin_user_id])


class AppConfigOverride(db.Model):
    """Durable administrator configuration overrides stored in the database.

    Overrides persist across worker restarts and are merged into the effective
    configuration on every request via ``app.config_store``.
    """
    __tablename__ = 'app_config_override'
    key = db.Column(db.String(128), primary_key=True)
    value = db.Column(db.Text, nullable=False)
    updated_by = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True
    )
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        index=True,
    )
    updated_by_user = db.relationship('User', foreign_keys=[updated_by])

    def get_value(self):
        """Deserialize the stored JSON value, falling back to raw text."""
        import json
        try:
            return json.loads(self.value)
        except (ValueError, TypeError):
            return self.value


class LessonBookmark(db.Model):
    """User bookmarks for lessons."""
    __tablename__ = 'lesson_bookmark'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    lesson_id = db.Column(db.String(100), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, nullable=False
    )
    __table_args__ = (
        db.UniqueConstraint('user_id', 'lesson_id', name='unique_user_lesson_bookmark'),
        db.Index('idx_lessonbookmark_user', 'user_id'),
    )


class LessonNote(db.Model):
    """User notes attached to lessons."""
    __tablename__ = 'lesson_note'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    lesson_id = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    __table_args__ = (
        db.UniqueConstraint('user_id', 'lesson_id', name='unique_user_lesson_note'),
        db.Index('idx_lessonnote_user', 'user_id'),
    )


class SupportRequest(db.Model):
    """Private learner reports and suggestions for the support team."""
    __tablename__ = 'support_request'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    category = db.Column(db.String(24), nullable=False)
    subject = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    page_url = db.Column(db.String(500))
    status = db.Column(
        db.String(24), nullable=False, default='new', server_default='new'
    )
    admin_reply = db.Column(db.Text)
    replied_at = db.Column(db.DateTime(timezone=True))
    replied_by_user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    __table_args__ = (
        db.Index('idx_support_request_created', 'created_at'),
        db.Index('idx_support_request_status', 'status'),
        db.Index('idx_support_request_user', 'user_id'),
    )


class PhoneVerificationCode(db.Model):
    """Short-lived SMS code proving the learner controls a phone number."""
    __tablename__ = 'phone_verification_code'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    phone = db.Column(db.String(50), nullable=False)
    code_hash = db.Column(db.String(64), unique=True, nullable=False)
    purpose = db.Column(
        db.String(20), nullable=False, default='verify_phone',
        server_default='verify_phone',
    )
    attempts = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (
        db.Index('idx_phone_verification_user', 'user_id', 'purpose'),
    )


class TutorConversation(db.Model):
    """Persistent conversation history between a learner and the AI tutor."""
    __tablename__ = 'tutor_conversation'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    lesson_id = db.Column(
        db.String(100), nullable=True,
        doc='Lesson ID if conversation is lesson-specific, otherwise None for general'
    )
    role = db.Column(
        db.String(20), nullable=False,
        doc='Role of the speaker: user or assistant'
    )
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow
    )
    __table_args__ = (
        db.Index('idx_tutor_conversation_user_lesson', 'user_id', 'lesson_id'),
        db.Index('idx_tutor_conversation_user', 'user_id'),
    )


class EngineeringLabCompletion(db.Model):
    """Persisted completion/reset evidence for Engineering Labs 2.0 scenarios."""
    __tablename__ = 'engineering_lab_completion'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    domain_id = db.Column(db.String(40), nullable=False)
    lab_id = db.Column(db.String(80), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='in_progress')  # in_progress, completed, reset
    evidence_notes = db.Column(db.Text)
    completed_at = db.Column(db.DateTime(timezone=True))
    reset_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'domain_id', 'lab_id', name='uq_engineering_lab_completion_user_lab'),
        db.Index('idx_engineering_lab_completion_user', 'user_id'),
    )


class ProjectLifecycleEvent(db.Model):
    """Append-only audit log for the shared project lifecycle (M2.3).

    One row per stage transition. Never updated or deleted; the current
    stage is derived from the newest row for (user_id, domain, project_key).
    Domain-specific assessment rules live in the AI/ML services; this table
    only records lifecycle transitions.
    """
    __tablename__ = 'project_lifecycle_event'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False,
        doc='Owner of the project',
    )
    domain = db.Column(db.String(40), nullable=False)  # ai-engineering | machine-learning
    project_key = db.Column(db.String(100), nullable=False)  # module_id
    from_stage = db.Column(db.String(32), nullable=True)
    to_stage = db.Column(db.String(32), nullable=False)
    actor_user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True,
        doc='Who performed the transition; NULL for automated/system transitions',
    )
    note = db.Column(db.String(300), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow,
    )
    __table_args__ = (
        db.Index('idx_project_lifecycle_owner_key', 'user_id', 'domain', 'project_key', 'id'),
    )


class ProjectMilestone(db.Model):
    """Per-deliverable milestone state for AI/ML module projects (M2.4).

    Milestone *definitions* come from the module's published deliverables in
    the canonical manifests; rows here record the learner's progress and
    notes against each deliverable. Assessment outcomes live in the AI/ML
    project services — this table only tracks milestones.
    """
    __tablename__ = 'project_milestone'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    domain = db.Column(db.String(40), nullable=False)  # ai-engineering | machine-learning
    project_key = db.Column(db.String(100), nullable=False)  # module_id
    milestone_id = db.Column(db.String(20), nullable=False)  # m1..mN index into deliverables
    completed = db.Column(
        db.Boolean, nullable=False, default=False, server_default=db.false()
    )
    note = db.Column(db.Text, nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
    __table_args__ = (
        db.UniqueConstraint(
            'user_id', 'domain', 'project_key', 'milestone_id',
            name='uq_project_milestone_user_key',
        ),
        db.Index('idx_project_milestone_user_project', 'user_id', 'domain', 'project_key'),
    )


class ProjectEvaluation(db.Model):
    """Traceable project evaluation evidence (M4).

    One row is one evaluation version for a learner's specialization project.
    Evidence is deliberately stored as three separate sources — automated
    checks, rubric feedback and optional human review — so no single generated
    score can stand in for project quality. Versions are append-only: a new
    submission writes a new row rather than overwriting an earlier decision.
    The row never decides mastery on its own; competency linkage additionally
    requires an approved/published lifecycle stage.
    """

    __tablename__ = 'project_evaluation'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    domain = db.Column(db.String(40), nullable=False)
    project_key = db.Column(db.String(100), nullable=False)
    version = db.Column(db.Integer, nullable=False)
    lifecycle_stage = db.Column(db.String(32), nullable=False)
    automated_checks_json = db.Column(db.Text, nullable=False)
    rubric_feedback_json = db.Column(db.Text, nullable=False)
    evidence_refs_json = db.Column(
        db.Text, nullable=False, default='[]', server_default='[]'
    )
    human_review_json = db.Column(db.Text, nullable=True)
    status = db.Column(
        db.String(24), nullable=False, default='AWAITING_HUMAN_REVIEW',
        server_default='AWAITING_HUMAN_REVIEW',
    )
    rubric_score = db.Column(db.Integer, nullable=True)
    created_by_user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True
    )
    reviewed_by_user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True
    )
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    __table_args__ = (
        db.UniqueConstraint(
            'user_id', 'domain', 'project_key', 'version',
            name='uq_project_evaluation_version',
        ),
        db.Index(
            'idx_project_evaluation_owner_key', 'user_id', 'domain',
            'project_key', 'id',
        ),
        db.Index('idx_project_evaluation_status', 'status', 'domain'),
    )

    def get_automated_checks(self):
        return json.loads(self.automated_checks_json or '{}')

    def get_rubric_feedback(self):
        return json.loads(self.rubric_feedback_json or '{}')

    def get_evidence_refs(self):
        return json.loads(self.evidence_refs_json or '[]')

    def get_human_review(self):
        return json.loads(self.human_review_json) if self.human_review_json else None


class ArenaRecommendationDismissal(db.Model):
    """A learner's dismissal of an Arena recommendation (M3.5).

    Dismissal is an explicit learner choice; it never removes content or
    blocks prerequisite rules — it only hides a recommendation until the
    underlying competency state changes.
    """
    __tablename__ = 'arena_recommendation_dismissal'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    problem_id = db.Column(db.String(120), nullable=False)
    dismissed_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow
    )
    __table_args__ = (
        db.UniqueConstraint('user_id', 'problem_id', name='uq_arena_rec_dismissal_user_problem'),
        db.Index('idx_arena_rec_dismissal_user', 'user_id'),
    )


class FoundationLessonProgress(db.Model):
    """Owner-scoped completion record for Shared Foundations lessons (M1).

    Deliberately separate from ``LessonCompletion`` (which pathway lessons
    share). Foundation unlocks depend only on earlier foundation lessons in
    the canonical chain — never on any AI/ML pathway lesson, module project,
    or legacy course state.
    """
    __tablename__ = 'foundation_lesson_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    lesson_id = db.Column(db.String(100), nullable=False)
    completed_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow
    )
    __table_args__ = (
        db.UniqueConstraint('user_id', 'lesson_id', name='uq_foundation_progress_user_lesson'),
        db.Index('idx_foundation_progress_user', 'user_id'),
    )
