from flask import (
    Blueprint, current_app, render_template, request, redirect, url_for,
    flash, jsonify,
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import PasswordResetToken, User
from app.phone import PhoneError, normalize_phone
from datetime import datetime, timedelta, timezone
import hashlib
import os
import secrets
from urllib.parse import urljoin, urlsplit

auth_bp = Blueprint('auth', __name__)


def safe_local_redirect(target):
    if not target:
        return False
    ref = urlsplit(urljoin(request.host_url, target))
    return ref.scheme in {'http', 'https'} and ref.netloc == request.host


def _password_reset_identifier(raw_identifier):
    if not isinstance(raw_identifier, str) or not raw_identifier.strip():
        return None, None
    identifier = raw_identifier.strip()
    if '@' in identifier:
        return 'email', identifier.lower()
    try:
        return 'phone', normalize_phone(identifier)
    except PhoneError:
        return None, None


def _password_reset_channels(user, identifier_kind, email_available, sms_available):
    """Choose delivery methods, preferring the identifier the learner used."""
    channels = []
    if identifier_kind == 'phone' and user.phone and sms_available:
        channels.append('sms')
    if user.email and email_available:
        channels.append('email')
    if user.phone and sms_available and 'sms' not in channels:
        channels.append('sms')
    return channels


def _deliver_password_reset(user, channels, reset_url):
    """Try each configured channel and return the one that succeeded."""
    from app.mail import send_password_reset_email
    from app.sms import send_password_reset_sms

    for channel in channels:
        try:
            if channel == 'sms':
                send_password_reset_sms(user.phone, reset_url)
            else:
                send_password_reset_email(user.email, reset_url)
            return channel
        except Exception:
            current_app.logger.exception(
                'Could not send password recovery %s for user %s',
                channel, user.id,
            )
    return None

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username') or request.form.get('email')
        password = request.form.get('password')
        email = username.strip().lower() if isinstance(username, str) else username
        user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if (
            user and user.password_hash
            and isinstance(password, str)
            and check_password_hash(user.password_hash, password)
        ):
            login_user(user)
            user.last_active = datetime.now(timezone.utc)
            db.session.commit()
            next_page = request.args.get('next') or request.form.get('next')
            return redirect(next_page) if safe_local_redirect(next_page) else redirect(url_for('main.index'))
        flash('Invalid username or password', 'error')

    return render_template(
        'auth/login.html', login_identifier=request.form.get('username', ''),
        next_page=request.args.get('next', ''),
    )


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    from app.mail import password_reset_mail_configured
    from app.sms import password_reset_sms_configured

    email_available = password_reset_mail_configured()
    sms_available = password_reset_sms_configured()
    recovery_available = (
        bool(current_app.config.get('TESTING'))
        or email_available
        or sms_available
    )
    context = {
        'recovery_available': recovery_available,
        'email_recovery_available': email_available,
        'sms_recovery_available': sms_available,
    }
    if request.method == 'GET':
        return render_template('auth/forgot_password.html', **context)
    if not recovery_available:
        return render_template('auth/forgot_password.html', **context), 503

    raw_identifier = request.form.get('identifier')
    if raw_identifier is None:
        raw_identifier = request.form.get('email')
    identifier_kind, identifier = _password_reset_identifier(raw_identifier)
    if not identifier_kind:
        flash('Enter the email address or phone number on your account.', 'error')
        return render_template(
            'auth/forgot_password.html',
            recovery_identifier=raw_identifier or '',
            **context,
        ), 200

    if identifier_kind == 'email':
        user = User.query.filter_by(email=identifier).first()
    else:
        user = User.query.filter_by(phone=identifier).first()
    if user:
        now = datetime.now(timezone.utc)
        recent = PasswordResetToken.query.filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.created_at >= now - timedelta(minutes=15),
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        ).first()
        if not recent:
            channels = _password_reset_channels(
                user, identifier_kind, email_available, sms_available
            )
            if channels:
                raw_token = secrets.token_urlsafe(32)
                token = PasswordResetToken(
                    user_id=user.id,
                    token_hash=hashlib.sha256(
                        raw_token.encode('utf-8')
                    ).hexdigest(),
                    expires_at=now + timedelta(minutes=30),
                )
                db.session.add(token)
                db.session.commit()
                public_url = os.environ.get('PUBLIC_APP_URL', '').rstrip('/')
                reset_url = (
                    public_url
                    + url_for('auth.reset_password', token=raw_token)
                )
                if not _deliver_password_reset(user, channels, reset_url):
                    db.session.delete(token)
                    db.session.commit()
    flash(
        'If an account exists for that email or phone number, password reset '
        'instructions will be sent.',
        'success',
    )
    return redirect(url_for('auth.login'))


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
    reset_token = PasswordResetToken.query.filter_by(
        token_hash=token_hash, used_at=None
    ).first()
    if not reset_token:
        flash('This password reset link is invalid or expired.', 'error')
        return redirect(url_for('auth.forgot_password'))
    expires_at = reset_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        flash('This password reset link is invalid or expired.', 'error')
        return redirect(url_for('auth.forgot_password'))
    if request.method == 'GET':
        return render_template('auth/reset_password.html', token=token)

    password = request.form.get('password')
    confirmation = request.form.get('confirm_password')
    if (
        not isinstance(password, str) or len(password) < 8
        or password != confirmation
    ):
        flash('Use matching passwords with at least 8 characters.', 'error')
        return render_template('auth/reset_password.html', token=token), 200
    user = db.session.get(User, reset_token.user_id)
    if user is None:
        flash('This password reset link is invalid or expired.', 'error')
        return redirect(url_for('auth.forgot_password'))
    user.password_hash = generate_password_hash(password)
    now = datetime.now(timezone.utc)
    PasswordResetToken.query.filter_by(user_id=user.id).update(
        {'used_at': now}, synchronize_session=False
    )
    db.session.commit()
    flash('Password updated. Sign in with your new password.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        raw_phone = (request.form.get('phone') or '').strip()
        password = request.form.get('password')
        full_name = (request.form.get('full_name') or '').strip()

        values = {
            'username': username,
            'email': email,
            'phone': raw_phone,
            'full_name': full_name,
        }
        errors = {}
        phone = None
        if not username:
            errors['username'] = 'Enter a username.'
        elif len(username) > 80:
            errors['username'] = 'Username must be 80 characters or fewer.'
        if not email:
            errors['email'] = 'Enter your email address.'
        elif len(email) > 120 or '@' not in email:
            errors['email'] = 'Enter a valid email address.'
        if raw_phone:
            if len(raw_phone) > 50:
                errors['phone'] = 'Phone number must be 50 characters or fewer.'
            else:
                try:
                    phone = normalize_phone(raw_phone)
                except PhoneError as error:
                    errors['phone'] = str(error)
        if not isinstance(password, str) or len(password) < 8:
            errors['password'] = 'Use a password with at least 8 characters.'
        elif password != request.form.get('confirm_password', password):
            errors['confirm_password'] = 'The passwords do not match.'
        if errors:
            return render_template(
                'auth/register.html', values=values, errors=errors,
                next_page=request.form.get('next', ''),
            ), 200
        
        if User.query.filter_by(username=username).first():
            errors['username'] = 'That username is already in use.'
        if email and User.query.filter_by(email=email).first():
            errors['email'] = 'An account with that email already exists.'
        if phone and User.query.filter_by(phone=phone).first():
            errors['phone'] = 'That phone number is already in use.'
        if errors:
            return render_template(
                'auth/register.html', values=values, errors=errors,
                next_page=request.form.get('next', ''),
            ), 200
        
        user = User(
            username=username,
            email=email,
            phone=phone,
            full_name=full_name,
            password_hash=generate_password_hash(password),
            created_at=datetime.now(timezone.utc),
            last_active=datetime.now(timezone.utc)
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Registration successful!', 'success')
        # Keep the destination through the required first-run setup.
        next_page = request.form.get('next', '')
        if safe_local_redirect(next_page):
            from flask import session
            session['_post_setup_next'] = next_page
        return redirect(url_for('main.index'))
    
    return render_template('auth/register.html', values={}, errors={})

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)


@auth_bp.route('/account/update', methods=['POST'])
@login_required
def update_account():
    from werkzeug.security import generate_password_hash, check_password_hash
    data = request.get_json(silent=True) if request.is_json else request.form
    if not hasattr(data, 'get'):
        return jsonify({'error': 'Request body must be an object'}), 400
    raw_email = data.get('email')
    raw_phone = data.get('phone')
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    if any(
        value is not None and not isinstance(value, str)
        for value in (raw_email, raw_phone, current_password, new_password)
    ):
        return jsonify({'error': 'Account fields must be strings'}), 400
    email = (raw_email or '').strip().lower() if raw_email is not None else None
    phone = (raw_phone or '').strip() if raw_phone is not None else None
    if email is not None and len(email) > 120:
        return jsonify({'error': 'Email must be 120 characters or fewer'}), 400
    if phone:
        try:
            phone = normalize_phone(phone)
        except PhoneError as error:
            if request.is_json:
                return {'error': str(error)}, 400
            flash(str(error), 'error')
            return redirect(url_for('auth.profile'))
        if User.query.filter(
            User.phone == phone, User.id != current_user.id
        ).first():
            if request.is_json:
                return {'error': 'Phone number already exists'}, 400
            flash('Phone number already exists', 'error')
            return redirect(url_for('auth.profile'))
    elif phone is not None:
        phone = None
    
    # Update email
    if email is not None and email != (current_user.email or ''):
        if email:
            if User.query.filter(User.email == email, User.id != current_user.id).first():
                if request.is_json:
                    return {'error': 'Email already exists'}, 400
                flash('Email already exists', 'error')
                return redirect(url_for('auth.profile'))
        current_user.email = email or None
    
    # Update phone
    if phone is not None:
        current_user.phone = phone
    
    # Update password
    if new_password:
        if not current_password or not current_user.password_hash or not check_password_hash(current_user.password_hash, current_password):
            if request.is_json:
                return {'error': 'Current password is incorrect'}, 400
            flash('Current password is incorrect', 'error')
            return redirect(url_for('auth.profile'))
        if len(new_password) < 8:
            if request.is_json:
                return {'error': 'Password must be at least 8 characters'}, 400
            flash('Password must be at least 8 characters', 'error')
            return redirect(url_for('auth.profile'))
        current_user.password_hash = generate_password_hash(new_password)
        PasswordResetToken.query.filter_by(user_id=current_user.id).update(
            {'used_at': datetime.now(timezone.utc)}, synchronize_session=False
        )
    
    db.session.commit()
    if request.is_json:
        return {'status': 'success'}
    flash('Account updated successfully', 'success')
    return redirect(url_for('auth.profile'))


@auth_bp.route('/account/delete', methods=['POST'])
@login_required
def delete_account():
    user = current_user
    user_id = user.id
    current_password = request.form.get('current_password')
    if request.is_json:
        data = request.get_json(silent=True)
        current_password = data.get('current_password') if isinstance(data, dict) else None
    if (
        not user.password_hash or not isinstance(current_password, str)
        or not check_password_hash(user.password_hash, current_password)
    ):
        if request.is_json:
            return {'error': 'Current password is incorrect'}, 400
        flash('Current password is incorrect', 'error')
        return redirect(url_for('auth.profile'))
    # Delete all related data explicitly for safety
    try:
        from app.routes.calendar import (
            perform_user_calendar_cleanup, prepare_user_calendar_cleanup,
        )
        try:
            calendar_cleanup = prepare_user_calendar_cleanup(user)
            calendar_cleanup_complete = perform_user_calendar_cleanup(
                calendar_cleanup, user_id
            )
        except Exception:
            current_app.logger.exception(
                'Could not prepare Calendar cleanup for deleted user %s', user_id
            )
            calendar_cleanup_complete = False
        if not calendar_cleanup_complete:
            db.session.rollback()
            if request.is_json:
                return {'error': 'Could not remove Google Calendar events; account was not deleted'}, 502
            flash(
                'Could not remove your Google Calendar events. Your account was not deleted; retry after reconnecting.',
                'error',
            )
            return redirect(url_for('auth.profile'))
        db.session.delete(user)
        db.session.commit()
        logout_user()
        flash('Account deleted permanently', 'info')
        if request.is_json:
            return {
                'status': 'success',
                'calendar_cleanup_complete': True,
            }
        return redirect(url_for('auth.login'))
    except Exception:
        db.session.rollback()
        if request.is_json:
            return {'error': 'Could not delete account'}, 500
        flash('Failed to delete account', 'error')
        return redirect(url_for('auth.profile'))


@auth_bp.route('/account/reset', methods=['POST'])
@login_required
def reset_account():
    user = current_user
    user_id = user.id
    current_password = request.form.get('current_password')
    if request.is_json:
        data = request.get_json(silent=True)
        current_password = data.get('current_password') if isinstance(data, dict) else None
    if (
        not user.password_hash or not isinstance(current_password, str)
        or not check_password_hash(user.password_hash, current_password)
    ):
        if request.is_json:
            return {'error': 'Current password is incorrect'}, 400
        flash('Current password is incorrect', 'error')
        return redirect(url_for('auth.profile'))
    try:
        from app.routes.calendar import (
            perform_user_calendar_cleanup, prepare_user_calendar_cleanup,
        )
        try:
            calendar_cleanup = prepare_user_calendar_cleanup(user)
            calendar_cleanup_complete = perform_user_calendar_cleanup(
                calendar_cleanup, user_id
            )
        except Exception:
            current_app.logger.exception(
                'Could not prepare Calendar cleanup for reset user %s', user_id
            )
            calendar_cleanup_complete = False
        if not calendar_cleanup_complete:
            db.session.rollback()
            if request.is_json:
                return {'error': 'Could not remove Google Calendar events; account was not reset'}, 502
            flash(
                'Could not remove your Google Calendar events. Your account was not reset; retry after reconnecting.',
                'error',
            )
            return redirect(url_for('auth.profile'))
        user = User.query.filter_by(id=user_id).with_for_update().populate_existing().one()
        # Delete all user data but keep the user account
        from app.models import (Progress, LessonCompletion, QuizResult, StudySession, 
                                UserSubjectConfig, ProficiencyTest, CalendarEvent,
                                UserSubject, UserSchedule, UserConfig,
                                SubjectCurriculum, LearningProject, CourseProject,
                                GeminiUsageBucket, AIBackgroundJob, ReviewItem,
                                VideoProgress)
        Progress.query.filter_by(user_id=user.id).delete()
        LessonCompletion.query.filter_by(user_id=user.id).delete()
        VideoProgress.query.filter_by(user_id=user.id).delete()
        QuizResult.query.filter_by(user_id=user.id).delete()
        StudySession.query.filter_by(user_id=user.id).delete()
        UserSubjectConfig.query.filter_by(user_id=user.id).delete()
        ProficiencyTest.query.filter_by(user_id=user.id).delete()
        CalendarEvent.query.filter_by(user_id=user.id).delete()
        SubjectCurriculum.query.filter_by(user_id=user.id).delete()
        LearningProject.query.filter_by(user_id=user.id).delete()
        CourseProject.query.filter_by(user_id=user.id).delete()
        GeminiUsageBucket.query.filter_by(user_id=user.id).delete()
        AIBackgroundJob.query.filter_by(user_id=user.id).delete()
        ReviewItem.query.filter_by(user_id=user.id).delete()
        PasswordResetToken.query.filter_by(user_id=user.id).delete()
        UserSubject.query.filter_by(user_id=user.id).delete()
        UserSchedule.query.filter_by(user_id=user.id).delete()
        UserConfig.query.filter_by(user_id=user.id).delete()
        user.google_access_token = None
        user.google_refresh_token = None
        user.token_expiry = None
        user.subjects_configured = False
        db.session.commit()
        flash('Account reset successfully', 'success')
        if request.is_json:
            return {
                'status': 'success',
                'calendar_cleanup_complete': True,
            }
        return redirect(url_for('main.index'))
    except Exception:
        db.session.rollback()
        if request.is_json:
            return {'error': 'Could not reset account'}, 500
        flash('Failed to reset account', 'error')
        return redirect(url_for('auth.profile'))
