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
    data = db.Column(db.LargeBinary, nullable=False)
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
    )

    def get_project(self):
        return json.loads(self.project) if self.project else {}

    def get_evaluation(self):
        return json.loads(self.evaluation) if self.evaluation else None


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
    leaderboard_opt_in = db.Column(
        db.Boolean, nullable=False, default=False, server_default=db.false()
    )
    track = db.Column(
        db.String(20), nullable=False, default='standard',
        server_default='standard',
    )
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


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
    available_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    locked_at = db.Column(db.DateTime(timezone=True))
    lease_token = db.Column(db.String(64))
    last_error = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
    __table_args__ = (
        db.Index('idx_ai_job_status_available', 'status', 'available_at'),
        db.Index('idx_ai_job_user', 'user_id'),
    )


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
    __table_args__ = (
        db.UniqueConstraint(
            'user_id', 'quiz_id', 'question_id', name='unique_review_question'
        ),
        db.Index('idx_review_due', 'user_id', 'active', 'due_at'),
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
