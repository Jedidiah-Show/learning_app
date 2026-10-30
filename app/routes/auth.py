from flask import (
    Blueprint, current_app, render_template, request, redirect, url_for,
    flash, jsonify, session, Response, abort,
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from app import db
from app.models import (
    CoursePlan, PasswordResetToken, PhoneVerificationCode, User, UserProfilePhoto,
)
from app.phone import PhoneError, normalize_phone
from app.rate_limit import client_ip, enforce_rate_limit, identity_hash
from app.course_data import (
    PACE_CHOICES, SKILL_LEVELS, TRACKS, recommend_track,
)
from datetime import datetime, timedelta, timezone
import hashlib
import os
import secrets
import uuid
from urllib.parse import urljoin, urlsplit

auth_bp = Blueprint('auth', __name__)
ALLOWED_PHOTO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def _allowed_photo_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_PHOTO_EXTENSIONS


def _photo_mime_type(filename, content):
    """Match the claimed extension to a supported raster image signature."""
    extension = filename.rsplit('.', 1)[1].lower()
    signatures = {
        'png': ('image/png', lambda value: value.startswith(b'\x89PNG\r\n\x1a\n')),
        'jpg': ('image/jpeg', lambda value: value.startswith(b'\xff\xd8\xff')),
        'jpeg': ('image/jpeg', lambda value: value.startswith(b'\xff\xd8\xff')),
        'gif': ('image/gif', lambda value: value.startswith((b'GIF87a', b'GIF89a'))),
        'webp': (
            'image/webp',
            lambda value: len(value) >= 12 and value[:4] == b'RIFF' and value[8:12] == b'WEBP',
        ),
    }
    match = signatures.get(extension)
    return match[0] if match and match[1](content) else None


def _set_auth_session(user):
    # Signing in through the learner portal never carries an existing admin
    # grant forward; administrators must re-authenticate inside /admin.
    session.pop('admin_user_id', None)
    session.pop('admin_authenticated_at', None)
    session['auth_version'] = int(user.auth_version or 0)
    session.permanent = True
    # Rotate the CSRF token on privilege change to defeat session fixation.
    session['_csrf_token'] = secrets.token_urlsafe(32)


def _bump_auth_version(user):
    user.auth_version = int(user.auth_version or 0) + 1
    return user.auth_version


def _password_matches(user, password):
    return bool(
        user.password_hash and isinstance(password, str)
        and check_password_hash(user.password_hash, password)
    )


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


def _issue_phone_verification_code(user):
    """Create and text a fresh 6-digit phone verification code for a user."""
    from app.sms import password_reset_sms_configured, send_phone_verification_sms

    if not (user.phone and password_reset_sms_configured()):
        return False
    PhoneVerificationCode.query.filter_by(
        user_id=user.id, purpose='verify_phone'
    ).delete(synchronize_session=False)
    code = f'{secrets.randbelow(1_000_000):06d}'
    db.session.add(PhoneVerificationCode(
        user_id=user.id,
        phone=user.phone,
        code_hash=hashlib.sha256(code.encode('utf-8')).hexdigest(),
        purpose='verify_phone',
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    ))
    db.session.commit()
    try:
        send_phone_verification_sms(user.phone, code)
    except Exception:
        current_app.logger.exception(
            'Could not send phone verification SMS for user %s', user.id
        )
        PhoneVerificationCode.query.filter_by(
            user_id=user.id, purpose='verify_phone'
        ).delete(synchronize_session=False)
        db.session.commit()
        return False
    return True

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username') or request.form.get('email')
        password = request.form.get('password')
        email = username.strip().lower() if isinstance(username, str) else username
        enforce_rate_limit(
            'login-ip', 20, 300, client_ip()
        )
        enforce_rate_limit(
            'login-account', 8, 300,
            f'{client_ip()}:{identity_hash(email or username)}',
        )
        user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if user and user.is_active and _password_matches(user, password):
            login_user(user)
            _set_auth_session(user)
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
    enforce_rate_limit('forgot-ip', 5, 900, client_ip())
    enforce_rate_limit(
        'forgot-identifier', 3, 900,
        f'{client_ip()}:{identity_hash(raw_identifier)}',
    )
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
                    # The learner was promised instructions through every
                    # configured channel and none arrived; surface loudly.
                    current_app.logger.error(
                        'Password recovery failed for user %s over all '
                        'configured channels %s; no reset was delivered.',
                        user.id, channels,
                    )
    flash(
        'If an account exists for that email or phone number, password reset '
        'instructions will be sent.',
        'success',
    )
    return redirect(url_for('auth.login'))


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        enforce_rate_limit(
            'reset-password', 20, 3600,
            f'{client_ip()}:{identity_hash(token)}',
        )
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
    user.auth_version = int(user.auth_version or 0) + 1
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
        enforce_rate_limit('register-ip', 10, 3600, client_ip())
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
        elif password != request.form.get('confirm_password', ''):
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
            public_id='RU-' + uuid.uuid4().hex[:8].upper(),
            created_at=datetime.now(timezone.utc),
            last_active=datetime.now(timezone.utc)
        )
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            if not errors:
                errors['form'] = (
                    'Registration could not be completed. Please try again.'
                )
            return render_template(
                'auth/register.html', values=values, errors=errors,
                next_page=request.form.get('next', ''),
            ), 200
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Registration could not be completed')
            errors['form'] = 'Registration could not be completed. Please try again.'
            return render_template(
                'auth/register.html', values=values, errors=errors,
                next_page=request.form.get('next', ''),
            ), 200
        login_user(user)
        _set_auth_session(user)
        flash('Registration successful!', 'success')
        if phone and _issue_phone_verification_code(user):
            flash('A verification code was texted to your phone number.', 'info')
        # Keep the destination through the required first-run setup.
        next_page = request.form.get('next', '')
        if safe_local_redirect(next_page):
            session['_post_setup_next'] = next_page
        return redirect(url_for('main.index'))
    
    return render_template('auth/register.html', values={}, errors={})

@auth_bp.route('/onboarding', methods=['GET', 'POST'])
@login_required
def onboarding():
    """Answer the two first-run questions: prior knowledge, then available hours.

    Both answers persist on ``CoursePlan``. The pace recommendation is displayed
    for the learner to accept or change; it is never written silently, and the
    explicit ``POST /api/course-plan/track`` endpoint stays the learner's choice.
    """
    plan = CoursePlan.query.filter_by(user_id=current_user.id).first()
    if plan is None:
        plan = CoursePlan(user_id=current_user.id, track='standard')
        db.session.add(plan)
    selected_skill = plan.skill_level or ''
    selected_hours = plan.weekly_hours
    selected_track = plan.track if plan.track in TRACKS else recommend_track(selected_hours)
    selected_hours_id = ''
    for pace in PACE_CHOICES:
        if pace['hours'] == selected_hours:
            selected_hours_id = pace['id']
            break
    if request.method == 'POST':
        skill_level = (request.form.get('skill_level') or '').strip()
        weekly_hours = (request.form.get('weekly_hours') or '').strip()
        track = (request.form.get('track') or '').strip()
        errors = {}
        if skill_level not in {level['id'] for level in SKILL_LEVELS}:
            errors['skill_level'] = 'Choose what you already know.'
        pace_ids = {pace['id'] for pace in PACE_CHOICES}
        hours = None
        if weekly_hours in pace_ids:
            hours = next(pace['hours'] for pace in PACE_CHOICES if pace['id'] == weekly_hours)
        elif weekly_hours.strip().isdigit():
            hours = int(weekly_hours.strip())
        if hours is None:
            errors['weekly_hours'] = 'Choose how many hours you can study each week.'
        if errors:
            return render_template(
                'onboarding.html', errors=errors, skills=SKILL_LEVELS, paces=PACE_CHOICES,
                tracks=TRACKS, selected_skill=skill_level, selected_hours=weekly_hours,
                selected_track=track if track in TRACKS else selected_track,
                recommended_track=selected_track,
            ), 200
        plan.skill_level = skill_level
        plan.weekly_hours = hours
        if track and track in TRACKS:
            plan.track = track
        db.session.commit()
        session['_onboarding_done'] = True
        session.pop('_post_setup_next', None)
        next_page = request.form.get('next') or ''
        return redirect(next_page) if safe_local_redirect(next_page) else redirect(url_for('main.index'))
    return render_template(
        'onboarding.html', errors={}, skills=SKILL_LEVELS, paces=PACE_CHOICES,
        tracks=TRACKS, selected_skill=selected_skill, selected_hours=selected_hours_id,
        selected_track=selected_track, recommended_track=selected_track,
    )

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    session.pop('admin_user_id', None)
    session.pop('admin_authenticated_at', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    from app.sms import password_reset_sms_configured

    return render_template(
        'auth/profile.html', user=current_user,
        phone_verification_available=(
            bool(current_user.phone) and password_reset_sms_configured()
        ),
    )


@auth_bp.route('/account/verify-phone', methods=['POST'])
@login_required
def verify_phone():
    from app.sms import password_reset_sms_configured

    if not (current_user.phone and password_reset_sms_configured()):
        flash('Phone verification is not available for this account.', 'error')
        return redirect(url_for('auth.profile'))
    enforce_rate_limit(
        'phone_verify', 8, 900, identity_hash(str(current_user.id))
    )
    submitted = (request.form.get('code') or '').strip()
    if not submitted.isdigit():
        flash('Enter the 6-digit code from the text message.', 'error')
        return redirect(url_for('auth.profile'))
    code_hash = hashlib.sha256(submitted.encode('utf-8')).hexdigest()
    now = datetime.now(timezone.utc)
    record = PhoneVerificationCode.query.filter_by(
        user_id=current_user.id, purpose='verify_phone', code_hash=code_hash
    ).first()
    if record is None or record.expires_at <= now:
        flash('That code is invalid or expired. Request a new one.', 'error')
        return redirect(url_for('auth.profile'))
    record.attempts = int(record.attempts or 0) + 1
    if record.attempts > 5:
        db.session.delete(record)
        db.session.commit()
        flash('Too many incorrect attempts. Request a new code.', 'error')
        return redirect(url_for('auth.profile'))
    if len(submitted) != 6:
        db.session.commit()
        flash('That code is invalid or expired. Request a new one.', 'error')
        return redirect(url_for('auth.profile'))
    db.session.delete(record)
    current_user.phone_verified = True
    db.session.commit()
    flash('Phone number verified.', 'success')
    return redirect(url_for('auth.profile'))


@auth_bp.route('/account/verify-phone/resend', methods=['POST'])
@login_required
def resend_phone_verification():
    from app.sms import password_reset_sms_configured

    if not (current_user.phone and password_reset_sms_configured()):
        flash('Phone verification is not available for this account.', 'error')
        return redirect(url_for('auth.profile'))
    enforce_rate_limit(
        'phone_resend', 3, 1800, identity_hash(str(current_user.id))
    )
    if _issue_phone_verification_code(current_user):
        flash('A new verification code was texted to you.', 'success')
    else:
        flash('Could not send a verification code right now. Try again later.', 'error')
    return redirect(url_for('auth.profile'))


@auth_bp.route('/profile-photo/<int:user_id>')
@login_required
def profile_photo(user_id):
    if user_id != current_user.id and not current_user.is_admin:
        abort(404)
    photo = UserProfilePhoto.query.filter_by(user_id=user_id).first_or_404()
    response = Response(photo.data, mimetype=photo.mime_type)
    response.headers['Cache-Control'] = 'private, no-cache, max-age=0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@auth_bp.route('/account/update', methods=['POST'])
@login_required
def update_account():
    data = request.get_json(silent=True) if request.is_json else request.form
    if not hasattr(data, 'get'):
        return jsonify({'error': 'Request body must be an object'}), 400
    raw_email = data.get('email')
    raw_phone = data.get('phone')
    raw_full_name = data.get('full_name')
    raw_profile_photo = data.get('profile_photo')
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    remove_profile_photo = str(data.get('remove_profile_photo') or '').lower() in {
        '1', 'true', 'yes', 'on',
    }
    if any(
        value is not None and not isinstance(value, str)
        for value in (raw_email, raw_phone, current_password, new_password, raw_full_name, raw_profile_photo)
    ):
        return jsonify({'error': 'Account fields must be strings'}), 400
    email = (raw_email or '').strip().lower() if raw_email is not None else None
    phone = (raw_phone or '').strip() if raw_phone is not None else None
    full_name = (raw_full_name or '').strip() if raw_full_name is not None else None
    profile_photo = (raw_profile_photo or '').strip() if raw_profile_photo is not None else None
    if profile_photo and len(profile_photo) > 500:
        if request.is_json:
            return {'error': 'Profile photo URL must be 500 characters or fewer'}, 400
        flash('Profile photo URL must be 500 characters or fewer', 'error')
        return redirect(url_for('auth.profile'))
    elif profile_photo == '':
        profile_photo = None
    if full_name == '':
        full_name = None

    photo_file = request.files.get('profile_photo_file')
    photo_file_uploaded = False
    photo_data = None
    photo_mime_type = None
    if photo_file and photo_file.filename:
        if not _allowed_photo_file(photo_file.filename):
            flash('Profile photo must be a PNG, JPG, JPEG, GIF, or WebP image.', 'error')
            return redirect(url_for('auth.profile'))
        photo_data = photo_file.read(2 * 1024 * 1024 + 1)
        if len(photo_data) > 2 * 1024 * 1024:
            flash('Profile photo must be 2MB or smaller.', 'error')
            return redirect(url_for('auth.profile'))
        photo_mime_type = _photo_mime_type(photo_file.filename, photo_data)
        if not photo_mime_type:
            flash('Choose a valid PNG, JPG, GIF, or WebP image.', 'error')
            return redirect(url_for('auth.profile'))
        profile_photo = url_for(
            'auth.profile_photo', user_id=current_user.id, v=uuid.uuid4().hex
        )
        photo_file_uploaded = True
    elif remove_profile_photo:
        profile_photo = None

    if email is not None and (
        len(email) > 120 or (email and '@' not in email)
    ):
        return jsonify(
            {'error': 'Enter a valid email address of 120 characters or fewer'}
        ), 400
    if phone:
        try:
            phone = normalize_phone(phone)
        except PhoneError as error:
            if request.is_json:
                return {'error': str(error)}, 400
            flash(str(error), 'error')
            return redirect(url_for('auth.profile'))
    elif phone is not None:
        phone = None

    email_changed = (
        email is not None and (email or None) != (current_user.email or None)
    )
    phone_changed = (
        phone is not None and (phone or None) != (current_user.phone or None)
    )
    full_name_changed = (
        full_name is not None and (full_name or None) != (current_user.full_name or None)
    )
    profile_photo_changed = remove_profile_photo or (
        profile_photo is not None and (profile_photo or None) != (current_user.profile_photo or None)
    )
    password_changed = bool(new_password)

    if email_changed or phone_changed or password_changed:
        if not _password_matches(current_user, current_password):
            if request.is_json:
                return {'error': 'Current password is incorrect'}, 400
            flash('Current password is incorrect', 'error')
            return redirect(url_for('auth.profile'))

    if email_changed and email:
        if User.query.filter(
            User.email == email, User.id != current_user.id
        ).first():
            if request.is_json:
                return {'error': 'Email already exists'}, 400
            flash('Email already exists', 'error')
            return redirect(url_for('auth.profile'))
    if phone_changed and phone:
        if User.query.filter(
            User.phone == phone, User.id != current_user.id
        ).first():
            if request.is_json:
                return {'error': 'Phone number already exists'}, 400
            flash('Phone number already exists', 'error')
            return redirect(url_for('auth.profile'))
    if password_changed and len(new_password) < 8:
        if request.is_json:
            return {'error': 'Password must be at least 8 characters'}, 400
        flash('Password must be at least 8 characters', 'error')
        return redirect(url_for('auth.profile'))

    if email_changed:
        current_user.email = email or None
    if phone_changed:
        current_user.phone = phone
        current_user.phone_verified = False
    if full_name_changed and full_name is not None:
        current_user.full_name = full_name
    if photo_file_uploaded:
        photo = UserProfilePhoto.query.filter_by(user_id=current_user.id).first()
        if photo is None:
            photo = UserProfilePhoto(user_id=current_user.id)
            db.session.add(photo)
        photo.data = photo_data
        photo.mime_type = photo_mime_type
        current_user.profile_photo = profile_photo
    elif remove_profile_photo:
        UserProfilePhoto.query.filter_by(user_id=current_user.id).delete()
        current_user.profile_photo = None
    elif profile_photo_changed and profile_photo is not None:
        current_user.profile_photo = profile_photo
    if password_changed:
        current_user.password_hash = generate_password_hash(new_password)
        PasswordResetToken.query.filter_by(user_id=current_user.id).update(
            {'used_at': datetime.now(timezone.utc)}, synchronize_session=False
        )

    if email_changed or phone_changed or password_changed:
        _bump_auth_version(current_user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if request.is_json:
            return {'error': 'Email or phone number already exists'}, 400
        flash('Email or phone number already exists', 'error')
        return redirect(url_for('auth.profile'))

    if email_changed or phone_changed or password_changed:
        _set_auth_session(current_user)
    if phone_changed and phone and _issue_phone_verification_code(current_user):
        flash('A new verification code was texted to your phone number.', 'info')
    if request.is_json:
        return {'status': 'success'}
    flash('Account updated successfully', 'success')
    return redirect(url_for('auth.profile'))


def _account_action_payload():
    if request.is_json:
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else {}
    return request.form


def _force_local_requested(data):
    value = data.get('force_local')
    if isinstance(value, bool):
        return value
    return str(value or '').lower() in {'1', 'true', 'yes', 'on'}


def _run_calendar_cleanup(user):
    """Return ``(complete, error)`` without making local account actions fail."""
    from app.routes.calendar import (
        perform_user_calendar_cleanup, prepare_user_calendar_cleanup,
    )

    try:
        cleanup = prepare_user_calendar_cleanup(user)
        return perform_user_calendar_cleanup(cleanup, user.id), None
    except Exception as error:
        db.session.rollback()
        current_app.logger.exception(
            'Could not clean up Google Calendar for user %s', user.id
        )
        return False, error


def _calendar_cleanup_required_response(action, force_local):
    if force_local:
        return None
    if request.is_json:
        return {
            'error': (
                'Could not finish removing Google Calendar events; your '
                f'account was not changed so {action} was not completed. '
                'Retry after reconnecting, or resend with '
                '"force_local": true to continue without remote cleanup.'
            ),
            'force_local_required': True,
        }, 502
    flash(
        'Could not finish removing your Google Calendar events. Your account '
        'was not changed. Retry after reconnecting, or select "continue '
        f'locally" and submit again to {action} without remote cleanup.',
        'error',
    )
    return redirect(url_for('auth.profile'))


@auth_bp.route('/account/delete', methods=['POST'])
@login_required
def delete_account():
    user = current_user
    user_id = user.id
    data = _account_action_payload()
    current_password = data.get('current_password')
    force_local = _force_local_requested(data)
    if not _password_matches(user, current_password):
        if request.is_json:
            return {'error': 'Current password is incorrect'}, 400
        flash('Current password is incorrect', 'error')
        return redirect(url_for('auth.profile'))

    try:
        from app import google_calendar as gcal

        calendar_cleanup_complete, _ = _run_calendar_cleanup(user)
        if not calendar_cleanup_complete:
            response = _calendar_cleanup_required_response(
                'delete your account', force_local
            )
            if response is not None:
                return response
        google_revoked = gcal.revoke_authorization(user)
        db.session.delete(user)
        db.session.commit()
        logout_user()
        flash('Account deleted permanently', 'info')
        if request.is_json:
            return {
                'status': 'success',
                'calendar_cleanup_complete': calendar_cleanup_complete,
                'force_local': force_local and not calendar_cleanup_complete,
                'google_revoked': google_revoked,
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
    data = _account_action_payload()
    current_password = data.get('current_password')
    force_local = _force_local_requested(data)
    if not _password_matches(user, current_password):
        if request.is_json:
            return {'error': 'Current password is incorrect'}, 400
        flash('Current password is incorrect', 'error')
        return redirect(url_for('auth.profile'))

    try:
        from app import google_calendar as gcal

        calendar_cleanup_complete, _ = _run_calendar_cleanup(user)
        if not calendar_cleanup_complete:
            response = _calendar_cleanup_required_response(
                'reset your account', force_local
            )
            if response is not None:
                return response
        google_revoked = gcal.revoke_authorization(user)
        user = db.session.execute(
            db.select(User).filter_by(id=user_id).with_for_update().execution_options(populate_existing=True)
        ).scalar_one()
        # Delete all user data but keep the account.  The AI usage bucket is
        # intentionally preserved so resetting cannot be used to bypass the
        # shared per-learner quota.
        from app.models import (
            Progress, LessonCompletion, QuizResult, StudySession,
            UserSubjectConfig, ProficiencyTest, CalendarEvent,
            UserSubject, UserSchedule, UserConfig,
            SubjectCurriculum, LearningProject, CourseProject,
            AIBackgroundJob, ReviewItem, VideoProgress, PracticeWorkspace,
        )
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
        PracticeWorkspace.query.filter_by(user_id=user.id).delete()
        AIBackgroundJob.query.filter_by(user_id=user.id).delete()
        ReviewItem.query.filter_by(user_id=user.id).delete()
        PasswordResetToken.query.filter_by(user_id=user.id).delete()
        UserSubject.query.filter_by(user_id=user.id).delete()
        UserSchedule.query.filter_by(user_id=user.id).delete()
        UserConfig.query.filter_by(user_id=user.id).delete()
        user.google_access_token = None
        user.google_refresh_token = None
        user.google_id = None
        user.token_expiry = None
        user.subjects_configured = False
        _bump_auth_version(user)
        db.session.commit()
        _set_auth_session(user)
        flash('Account reset successfully', 'success')
        if request.is_json:
            return {
                'status': 'success',
                'calendar_cleanup_complete': calendar_cleanup_complete,
                'force_local': force_local and not calendar_cleanup_complete,
                'google_revoked': google_revoked,
            }
        return redirect(url_for('main.index'))
    except Exception:
        db.session.rollback()
        if request.is_json:
            return {'error': 'Could not reset account'}, 500
        flash('Failed to reset account', 'error')
        return redirect(url_for('auth.profile'))
