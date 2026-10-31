"""Dedicated administrator portal.

This blueprint is intentionally separate from the learner experience: it has
its own sign-in page, its own layout, a short-lived admin session, and an
audit trail for every account-changing action.  Learner sessions never grant
admin access on their own; an administrator must explicitly authenticate at
``/admin/login``.
"""

from datetime import datetime, timedelta, timezone
from functools import wraps
import json

from flask import (
    Blueprint, abort, current_app, flash, jsonify, redirect, render_template,
    request, session, url_for,
)
from flask_login import current_user, login_user, logout_user
from sqlalchemy import distinct, func, or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.curriculum import all_lessons, all_modules
from app.integrations import database_status
from app.learning import course_progress
from app.models import (
    AdminAuditLog, CourseProject, Credential, LessonCompletion,
    MLSpecializationCredential, MLSpecializationLessonCompletion,
    MLSpecializationProject,
    PasswordResetToken, QuizResult, StudySession, SupportRequest, User,
)
from app.phone import PhoneError, normalize_phone
from app.rate_limit import client_ip, enforce_rate_limit, identity_hash

admin_portal_bp = Blueprint('admin_portal', __name__)

ADMIN_SESSION_MINUTES = 30
PAGE_SIZE = 20


def _utcnow():
    """UTC now in the aware form used by every application timestamp column."""
    return datetime.now(timezone.utc)


def _password_matches(user, password):
    return bool(
        user is not None and user.password_hash
        and isinstance(password, str)
        and check_password_hash(user.password_hash, password)
    )


def _admin_session_valid(user=None):
    """Return True when this browser holds a fresh admin session."""
    user = user or current_user
    if not getattr(user, 'is_authenticated', False):
        return False
    if not getattr(user, 'is_admin', False):
        return False
    if not getattr(user, 'is_active', True):
        return False
    try:
        admin_user_id = int(session.get('admin_user_id'))
        authenticated_at = float(session.get('admin_authenticated_at'))
    except (TypeError, ValueError):
        return False
    if admin_user_id != user.id:
        return False
    issued_at = datetime.fromtimestamp(authenticated_at, tz=timezone.utc)
    return datetime.now(timezone.utc) - issued_at <= timedelta(
        minutes=ADMIN_SESSION_MINUTES
    )


def _safe_admin_next(target):
    """Only allow redirects back into the admin portal."""
    if not isinstance(target, str):
        return None
    target = target.strip()
    if target.endswith('?'):
        target = target[:-1]
    if not target or target.startswith('//') or '\\' in target:
        return None
    if target == '/admin' or target.startswith('/admin/') or target.startswith('/admin?'):
        return target
    return None


def admin_required(view):
    """Require a signed-in, active administrator with a fresh admin session."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for(
                'admin_portal.login', next=request.full_path
            ))
        if (
            not getattr(current_user, 'is_admin', False)
            or not getattr(current_user, 'is_active', True)
        ):
            abort(403, description='The admin portal is available to administrators only.')
        if not _admin_session_valid(current_user):
            return redirect(url_for(
                'admin_portal.login', next=request.full_path
            ))
        return view(*args, **kwargs)

    return wrapped


def _record_admin_action(action, target_user_id=None, detail=None):
    """Stage an audit entry; the caller commits with the rest of the change."""
    entry = AdminAuditLog(
        admin_user_id=current_user.id if current_user.is_authenticated else None,
        action=action,
        target_user_id=target_user_id,
        detail=(detail or '')[:2000] or None,
        ip_address=client_ip(),
        created_at=_utcnow(),
    )
    db.session.add(entry)
    return entry


def _last_active_admin_remaining(exclude_user_id):
    return User.query.filter(
        User.id != exclude_user_id,
        User.is_admin.is_(True),
        User.is_active.is_(True),
    ).count() > 0


def _account_label(account):
    return account.username or account.email or f'user #{account.id}'


@admin_portal_bp.after_request
def add_admin_cache_headers(response):
    """Never cache privileged pages in browsers or shared proxies."""
    response.headers['Cache-Control'] = 'no-store, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response


@admin_portal_bp.context_processor
def inject_admin_state():
    return {
        'admin_authenticated': (
            _admin_session_valid() if current_user.is_authenticated else False
        ),
        'admin_session_minutes': ADMIN_SESSION_MINUTES,
    }


@admin_portal_bp.route('/login', methods=['GET', 'POST'])
def login():
    if _admin_session_valid():
        return redirect(url_for('admin_portal.dashboard'))

    identifier = ''
    next_page = request.args.get('next') or ''
    if request.method == 'POST':
        next_page = request.form.get('next') or next_page
        identifier = (
            request.form.get('identifier')
            or request.form.get('username')
            or request.form.get('email')
            or ''
        ).strip()
        password = request.form.get('password')
        enforce_rate_limit('admin-login-ip', 10, 300, client_ip())
        enforce_rate_limit(
            'admin-login-account', 5, 300,
            f'{client_ip()}:{identity_hash(identifier)}',
        )
        account = None
        if identifier:
            account = User.query.filter(or_(
                User.username == identifier,
                User.email == identifier.lower(),
            )).first()
        if (
            _password_matches(account, password)
            and account.is_admin
            and account.is_active
        ):
            login_user(account)
            session['auth_version'] = int(account.auth_version or 0)
            session['admin_user_id'] = account.id
            session['admin_authenticated_at'] = datetime.now(
                timezone.utc
            ).timestamp()
            account.last_active = _utcnow()
            _record_admin_action(
                'admin.login', target_user_id=account.id,
                detail='Administrator signed in to the portal.',
            )
            db.session.commit()
            target = _safe_admin_next(next_page)
            return redirect(target or url_for('admin_portal.dashboard'))
        current_app.logger.warning(
            'Failed administrator sign-in for %r from %s',
            identifier[:80], client_ip(),
        )
        flash('Invalid administrator credentials.', 'error')

    return render_template(
        'admin/login.html',
        identifier=identifier,
        next_page=next_page,
    )


@admin_portal_bp.route('/logout', methods=['POST'])
@admin_required
def logout():
    _record_admin_action(
        'admin.logout', target_user_id=current_user.id,
        detail='Administrator signed out of the portal.',
    )
    db.session.commit()
    logout_user()
    session.pop('admin_user_id', None)
    session.pop('admin_authenticated_at', None)
    flash('You have been signed out of the admin portal.', 'success')
    return redirect(url_for('admin_portal.login'))


@admin_portal_bp.route('/exit')
@admin_required
def exit_portal():
    """Leave the admin shell but keep the learner session alive."""
    session.pop('admin_user_id', None)
    session.pop('admin_authenticated_at', None)
    flash('Admin portal closed. You are back in the learner portal.', 'success')
    return redirect(url_for('main.index'))


@admin_portal_bp.route('')
@admin_portal_bp.route('/')
@admin_required
def dashboard():
    since = _utcnow() - timedelta(days=30)
    total_users = User.query.count()
    active_accounts = User.query.filter(User.is_active.is_(True)).count()
    active_admins = User.query.filter(
        User.is_admin.is_(True), User.is_active.is_(True)
    ).count()
    active_learners = User.query.filter(
        User.last_active >= since, User.is_active.is_(True)
    ).count()
    new_users = User.query.filter(User.created_at >= since).count()
    total_completions = LessonCompletion.query.filter_by(completed=True).count()
    total_projects = CourseProject.query.filter_by(completed=True).count()
    lessons = all_lessons()
    modules = all_modules()
    recent_completions = LessonCompletion.query.filter_by(
        completed=True
    ).order_by(LessonCompletion.completed_at.desc()).limit(8).all()
    recent_audit = AdminAuditLog.query.order_by(
        AdminAuditLog.created_at.desc()
    ).limit(8).all()
    ml_enrolled = db.session.query(
        func.count(distinct(MLSpecializationLessonCompletion.user_id))
    ).scalar() or 0
    ml_completed = db.session.query(
        func.count(distinct(MLSpecializationCredential.user_id))
    ).filter(MLSpecializationCredential.revoked_at.is_(None)).scalar() or 0
    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        active_accounts=active_accounts,
        disabled_accounts=total_users - active_accounts,
        active_admins=active_admins,
        active_learners=active_learners,
        new_users=new_users,
        total_completions=total_completions,
        total_projects=total_projects,
        total_lessons=len(lessons),
        total_modules=len(modules),
        ml_enrolled=ml_enrolled,
        ml_completed=ml_completed,
        recent_completions=recent_completions,
        recent_audit=recent_audit,
        database=database_status(),
    )


@admin_portal_bp.route('/users')
@admin_required
def users():
    search = (request.args.get('q') or '').strip()
    role = request.args.get('role') or 'all'
    status = request.args.get('status') or 'all'
    sort = request.args.get('sort') or 'newest'
    page = max(1, request.args.get('page', 1, type=int) or 1)

    query = User.query
    if search:
        like = f'%{search}%'
        query = query.filter(or_(
            User.username.ilike(like),
            User.email.ilike(like),
            User.full_name.ilike(like),
            User.phone.ilike(like),
        ))
    if role == 'admin':
        query = query.filter(User.is_admin.is_(True))
    elif role == 'learner':
        query = query.filter(User.is_admin.is_(False))
    if status == 'active':
        query = query.filter(User.is_active.is_(True))
    elif status == 'disabled':
        query = query.filter(User.is_active.is_(False))

    order = {
        'newest': User.created_at.desc(),
        'oldest': User.created_at.asc(),
        'active': User.last_active.desc(),
        'name': User.username.asc(),
    }.get(sort, User.created_at.desc())
    pagination = query.order_by(order).paginate(
        page=page, per_page=PAGE_SIZE, error_out=False
    )

    user_ids = [account.id for account in pagination.items]
    progress_by_user = {}
    if user_ids:
        progress_by_user = dict(
            db.session.query(
                LessonCompletion.user_id,
                func.count(LessonCompletion.id),
            ).filter(
                LessonCompletion.completed.is_(True),
                LessonCompletion.user_id.in_(user_ids),
            ).group_by(LessonCompletion.user_id).all()
        )

    return render_template(
        'admin/users.html',
        users=pagination.items,
        pagination=pagination,
        progress_by_user=progress_by_user,
        total_lessons=len(all_lessons()),
        search=search,
        role=role,
        status=status,
        sort=sort,
    )


def _validate_account_values(values, account_id=None):
    errors = {}
    username = values.get('username') or ''
    email = values.get('email') or ''
    phone = values.get('phone')
    if not username:
        errors['username'] = 'Enter a username.'
    elif len(username) > 80:
        errors['username'] = 'Username must be 80 characters or fewer.'
    if not email:
        errors['email'] = 'Enter an email address.'
    elif len(email) > 120 or '@' not in email:
        errors['email'] = 'Enter a valid email address.'
    if phone and len(phone) > 50:
        errors['phone'] = 'Phone number must be 50 characters or fewer.'

    if 'username' not in errors:
        clash = User.query.filter(User.username == username)
        if account_id is not None:
            clash = clash.filter(User.id != account_id)
        if clash.first():
            errors['username'] = 'That username is already in use.'
    if 'email' not in errors:
        clash = User.query.filter(User.email == email)
        if account_id is not None:
            clash = clash.filter(User.id != account_id)
        if clash.first():
            errors['email'] = 'An account with that email already exists.'
    if phone and 'phone' not in errors:
        clash = User.query.filter(User.phone == phone)
        if account_id is not None:
            clash = clash.filter(User.id != account_id)
        if clash.first():
            errors['phone'] = 'That phone number is already in use.'
    return errors


def _parse_phone(raw_phone, errors):
    if not raw_phone:
        return None
    try:
        return normalize_phone(raw_phone)
    except PhoneError as error:
        errors['phone'] = str(error)
        return None


@admin_portal_bp.route('/users/new', methods=['GET', 'POST'])
@admin_required
def create_user():
    values = {
        'username': '', 'email': '', 'full_name': '', 'phone': '',
        'is_admin': False,
    }
    errors = {}
    if request.method == 'POST':
        values = {
            'username': (request.form.get('username') or '').strip(),
            'email': (request.form.get('email') or '').strip().lower(),
            'full_name': (request.form.get('full_name') or '').strip(),
            'phone': (request.form.get('phone') or '').strip(),
            'is_admin': request.form.get('is_admin') in {'1', 'true', 'on'},
        }
        password = request.form.get('password')
        confirmation = request.form.get('confirm_password')
        errors = {}
        phone = _parse_phone(values['phone'], errors)
        errors.update(_validate_account_values(
            {**values, 'phone': phone or ''}
        ))
        if not isinstance(password, str) or len(password) < 8:
            errors['password'] = 'Use a password with at least 8 characters.'
        elif password != confirmation:
            errors['confirm_password'] = 'The passwords do not match.'
        if not errors:
            account = User(
                username=values['username'],
                email=values['email'],
                full_name=values['full_name'] or None,
                phone=phone,
                password_hash=generate_password_hash(password),
                is_admin=values['is_admin'],
                is_active=True,
                created_at=datetime.now(timezone.utc),
                last_active=None,
            )
            db.session.add(account)
            try:
                db.session.flush()
                _record_admin_action(
                    'user.create', target_user_id=account.id,
                    detail=(
                        f'Created {values["username"]} '
                        f'({values["email"]}) as '
                        f'{"administrator" if values["is_admin"] else "learner"}.'
                    ),
                )
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                errors['form'] = (
                    'An account with that username, email, or phone number '
                    'already exists.'
                )
            else:
                flash(
                    f'Account “{_account_label(account)}” was created.',
                    'success',
                )
                return redirect(url_for(
                    'admin_portal.user_detail', user_id=account.id
                ))
    return render_template(
        'admin/user_new.html', values=values, errors=errors
    )


@admin_portal_bp.route('/users/<int:user_id>')
@admin_required
def user_detail(user_id):
    account = db.session.get(User, user_id)
    if account is None:
        abort(404)
    progress = course_progress(account)
    total_minutes = db.session.query(
        func.coalesce(func.sum(StudySession.duration_minutes), 0)
    ).filter(StudySession.user_id == account.id).scalar()
    completions = LessonCompletion.query.filter_by(
        user_id=account.id, completed=True
    ).order_by(LessonCompletion.completed_at.desc()).limit(10).all()
    audit_entries = AdminAuditLog.query.filter(
        or_(
            AdminAuditLog.target_user_id == account.id,
            AdminAuditLog.admin_user_id == account.id,
        )
    ).order_by(AdminAuditLog.created_at.desc()).limit(10).all()
    credentials = Credential.query.filter_by(
        user_id=account.id
    ).order_by(Credential.issued_at.desc()).limit(5).all()
    return render_template(
        'admin/user_detail.html',
        account=account,
        progress=progress,
        total_minutes=int(total_minutes or 0),
        completions=completions,
        credentials=credentials,
        audit_entries=audit_entries,
    )


@admin_portal_bp.route('/users/<int:user_id>/profile', methods=['POST'])
@admin_required
def update_profile(user_id):
    account = db.session.get(User, user_id)
    if account is None:
        abort(404)
    values = {
        'username': (request.form.get('username') or '').strip(),
        'email': (request.form.get('email') or '').strip().lower(),
        'full_name': (request.form.get('full_name') or '').strip(),
        'phone': (request.form.get('phone') or '').strip(),
    }
    errors = {}
    phone = _parse_phone(values['phone'], errors)
    errors.update(_validate_account_values(
        {**values, 'phone': phone or ''}, account_id=account.id
    ))
    if errors:
        for message in errors.values():
            flash(message, 'error')
        return redirect(url_for(
            'admin_portal.user_detail', user_id=account.id
        ))

    changed = []
    if account.username != values['username']:
        account.username = values['username']
        changed.append('username')
    if (account.email or None) != (values['email'] or None):
        account.email = values['email'] or None
        changed.append('email')
    if (account.full_name or None) != (values['full_name'] or None):
        account.full_name = values['full_name'] or None
        changed.append('full name')
    if (account.phone or None) != (phone or None):
        account.phone = phone
        if phone is not None:
            account.phone_verified = False
        changed.append('phone')
    if 'username' in changed or 'email' in changed or 'phone' in changed:
        account.auth_version = int(account.auth_version or 0) + 1
        if account.id == current_user.id:
            session['auth_version'] = account.auth_version

    _record_admin_action(
        'user.update', target_user_id=account.id,
        detail=(
            'Updated ' + ', '.join(changed) if changed
            else 'Profile submitted with no changes.'
        ),
    )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('That username, email, or phone number is already in use.', 'error')
        return redirect(url_for(
            'admin_portal.user_detail', user_id=account.id
        ))
    flash(
        'Account details updated.' if changed else 'No changes were needed.',
        'success',
    )
    return redirect(url_for('admin_portal.user_detail', user_id=account.id))


@admin_portal_bp.route('/users/<int:user_id>/password', methods=['POST'])
@admin_required
def reset_password(user_id):
    account = db.session.get(User, user_id)
    if account is None:
        abort(404)
    password = request.form.get('password')
    confirmation = request.form.get('confirm_password')
    if not isinstance(password, str) or len(password) < 8:
        flash('Use a password with at least 8 characters.', 'error')
        return redirect(url_for(
            'admin_portal.user_detail', user_id=account.id
        ))
    if password != confirmation:
        flash('The passwords do not match.', 'error')
        return redirect(url_for(
            'admin_portal.user_detail', user_id=account.id
        ))
    account.password_hash = generate_password_hash(password)
    account.auth_version = int(account.auth_version or 0) + 1
    if account.id == current_user.id:
        session['auth_version'] = account.auth_version
    PasswordResetToken.query.filter_by(user_id=account.id, used_at=None).update(
        {'used_at': datetime.now(timezone.utc)}, synchronize_session=False
    )
    _record_admin_action(
        'user.password_reset', target_user_id=account.id,
        detail='Password reset by an administrator; existing sessions revoked.',
    )
    db.session.commit()
    flash(
        f'Password for “{_account_label(account)}” was reset. '
        'Their existing sessions have been signed out.',
        'success',
    )
    return redirect(url_for('admin_portal.user_detail', user_id=account.id))


def _requested_boolean(field, current):
    """Read a boolean from JSON or a form, falling back to a toggle."""
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        if field in payload:
            return bool(payload[field])
        return not current
    raw = request.form.get(field)
    if raw is None:
        return not current
    return str(raw).lower() in {'1', 'true', 'yes', 'on'}


def _wants_json():
    return request.is_json or 'application/json' in request.accept_mimetypes


@admin_portal_bp.route('/users/<int:user_id>/role', methods=['POST'])
@admin_required
def set_role(user_id):
    account = db.session.get(User, user_id)
    if account is None:
        abort(404)
    desired = _requested_boolean('is_admin', account.is_admin)
    if account.id == current_user.id and not desired:
        message = 'You cannot remove your own admin access.'
        if _wants_json():
            return jsonify({'error': message}), 400
        flash(message, 'error')
        return redirect(url_for(
            'admin_portal.user_detail', user_id=account.id
        ))
    if account.is_admin and not desired and not _last_active_admin_remaining(
        account.id
    ):
        message = 'At least one active administrator must remain.'
        if _wants_json():
            return jsonify({'error': message}), 400
        flash(message, 'error')
        return redirect(url_for(
            'admin_portal.user_detail', user_id=account.id
        ))
    if account.is_admin != desired:
        account.is_admin = desired
        _record_admin_action(
            'user.role_change', target_user_id=account.id,
            detail=(
                'Granted administrator access.'
                if desired else 'Removed administrator access.'
            ),
        )
        db.session.commit()
        flash(
            f'“{_account_label(account)}” is now '
            f'{"an administrator" if desired else "a learner"}.',
            'success',
        )
    if _wants_json():
        return jsonify({'status': 'success', 'is_admin': account.is_admin})
    return redirect(url_for('admin_portal.user_detail', user_id=account.id))


@admin_portal_bp.route('/users/<int:user_id>/status', methods=['POST'])
@admin_required
def set_status(user_id):
    account = db.session.get(User, user_id)
    if account is None:
        abort(404)
    desired = _requested_boolean('is_active', account.is_active)
    if account.id == current_user.id and not desired:
        message = 'You cannot deactivate your own account.'
        if _wants_json():
            return jsonify({'error': message}), 400
        flash(message, 'error')
        return redirect(url_for(
            'admin_portal.user_detail', user_id=account.id
        ))
    if (
        account.is_admin and account.is_active and not desired
        and not _last_active_admin_remaining(account.id)
    ):
        message = 'At least one active administrator must remain.'
        if _wants_json():
            return jsonify({'error': message}), 400
        flash(message, 'error')
        return redirect(url_for(
            'admin_portal.user_detail', user_id=account.id
        ))
    if account.is_active != desired:
        account.is_active = desired
        if not desired:
            account.auth_version = int(account.auth_version or 0) + 1
        _record_admin_action(
            'user.status_change', target_user_id=account.id,
            detail='Account activated.' if desired else 'Account deactivated.',
        )
        db.session.commit()
        flash(
            f'“{_account_label(account)}” was '
            f'{"activated" if desired else "deactivated"}.',
            'success',
        )
    if _wants_json():
        return jsonify({'status': 'success', 'is_active': account.is_active})
    return redirect(url_for('admin_portal.user_detail', user_id=account.id))


@admin_portal_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    account = db.session.get(User, user_id)
    if account is None:
        abort(404)
    if account.id == current_user.id:
        flash('You cannot delete your own account from the admin portal.', 'error')
        return redirect(url_for(
            'admin_portal.user_detail', user_id=account.id
        ))
    if account.is_admin and account.is_active and not _last_active_admin_remaining(
        account.id
    ):
        flash('At least one active administrator must remain.', 'error')
        return redirect(url_for(
            'admin_portal.user_detail', user_id=account.id
        ))
    confirmation = (request.form.get('confirmation') or '').strip()
    accepted = {
        (account.username or '').lower(),
        (account.email or '').lower(),
        'delete',
    }
    if confirmation.lower() not in accepted:
        flash(
            'Type the account username or email to confirm deletion.',
            'error',
        )
        return redirect(url_for(
            'admin_portal.user_detail', user_id=account.id
        ))

    label = _account_label(account)
    _record_admin_action(
        'user.delete', target_user_id=account.id,
        detail=f'Deleted account {label} ({account.email or "no email"}).',
    )
    db.session.delete(account)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        current_app.logger.exception(
            'Could not delete user %s because of related records', user_id
        )
        flash(
            'This account still owns records that cannot be removed '
            'automatically. Deactivate it instead.',
            'error',
        )
        return redirect(url_for(
            'admin_portal.user_detail', user_id=user_id
        ))
    flash(f'Account “{label}” was permanently deleted.', 'success')
    return redirect(url_for('admin_portal.users'))


@admin_portal_bp.route('/credentials/<public_id>/revoke', methods=['POST'])
@admin_required
def revoke_credential(public_id):
    credential = Credential.query.filter_by(public_id=public_id).first()
    if credential is None:
        abort(404)
    if credential.revoked_at is None:
        credential.revoked_at = _utcnow()
        _record_admin_action(
            'credential.revoke', target_user_id=credential.user_id,
            detail=f'Revoked credential {credential.public_id}.',
        )
        db.session.commit()
        flash('Credential revoked. Its public verification page now shows it as revoked.', 'success')
    else:
        flash('That credential was already revoked.', 'error')
    return redirect(url_for(
        'admin_portal.user_detail', user_id=credential.user_id
    ))


def _ml_pilot_snapshot():
    """Aggregate the Stage B pilot (Modules 1–2) for the analytics page.

    Read-only over the namespaced specialization tables; the runbook's
    caveats apply (project ``updated_at`` is overwritten by resubmissions,
    so time-to-project is an estimate unless snapshotted weekly).
    """
    from app.ml_pathway import PATHWAY_ID, machine_learning_lessons

    pilot_lessons = [
        lesson for lesson in machine_learning_lessons()
        if lesson.get('status') == 'ready' and lesson['module_number'] <= 2
    ]
    modules = []
    for lesson in pilot_lessons:
        if not any(entry['id'] == lesson['module_id'] for entry in modules):
            modules.append({
                'id': lesson['module_id'], 'title': lesson['module_title'],
            })
    module_ids = [entry['id'] for entry in modules]

    completions = db.session.query(
        MLSpecializationLessonCompletion.user_id,
        MLSpecializationLessonCompletion.lesson_id,
        MLSpecializationLessonCompletion.completed_at,
    ).join(User, User.id == MLSpecializationLessonCompletion.user_id).filter(
        MLSpecializationLessonCompletion.pathway_id == PATHWAY_ID,
        User.is_active.is_(True),
        User.is_admin.is_(False),
    ).all()
    per_lesson = {}
    per_learner = {}
    for user_id, lesson_id, completed_at in completions:
        entry = per_lesson.setdefault(lesson_id, {'count': set(), 'first': None, 'last': None})
        entry['count'].add(user_id)
        if entry['first'] is None or completed_at < entry['first']:
            entry['first'] = completed_at
        if entry['last'] is None or completed_at > entry['last']:
            entry['last'] = completed_at
        per_learner.setdefault(user_id, {})[lesson_id] = completed_at

    funnel = []
    for position, lesson in enumerate(pilot_lessons, start=1):
        entry = per_lesson.get(lesson['id'], {'count': set(), 'first': None, 'last': None})
        funnel.append({
            'position': position, 'title': lesson['title'],
            'module_number': lesson['module_number'],
            'completions': len(entry['count']),
            'first': entry['first'], 'last': entry['last'],
        })

    attempts = db.session.query(
        MLSpecializationProject, User,
    ).join(User, User.id == MLSpecializationProject.user_id).filter(
        MLSpecializationProject.pathway_id == PATHWAY_ID,
        MLSpecializationProject.module_id.in_(module_ids),
        User.is_active.is_(True),
        User.is_admin.is_(False),
    ).order_by(
        MLSpecializationProject.module_id, MLSpecializationProject.updated_at
    ).all()
    attempt_rows = []
    criteria_scores = {}
    passes = {}
    for record, learner in attempts:
        evaluation = None
        if record.evaluation:
            try:
                evaluation = json.loads(record.evaluation)
            except ValueError:
                evaluation = None
        score = None
        if isinstance(evaluation, dict) and isinstance(evaluation.get('score'), (int, float)):
            score = evaluation['score']
        if isinstance(evaluation, dict):
            for item in evaluation.get('criterion_feedback') or []:
                if isinstance(item, dict) and isinstance(item.get('score'), (int, float)):
                    criteria_scores.setdefault(
                        str(item.get('criterion', 'Unnamed criterion')), []
                    ).append(item['score'])
        label = learner.username or learner.email or f'User #{learner.id}'
        if record.completed:
            key = (record.user_id, record.module_id)
            if key not in passes or record.updated_at < passes[key]:
                passes[key] = record.updated_at
        attempt_rows.append({
            'learner': label, 'module_id': record.module_id,
            'completed': record.completed, 'score': score,
            'updated_at': record.updated_at,
        })

    times = []
    for (user_id, module_id), passed_at in passes.items():
        stamps = [
            completed_at for lesson_id, completed_at
            in per_learner.get(user_id, {}).items()
            if any(lesson['id'] == lesson_id and lesson['module_id'] == module_id
                   for lesson in pilot_lessons)
        ]
        if not stamps:
            continue
        days = round((passed_at - max(stamps)).total_seconds() / 86400, 1)
        if days >= 0:
            times.append({
                'user_id': user_id, 'module_id': module_id, 'days': days,
            })

    criteria = sorted((
        {'criterion': name, 'average': round(sum(scores) / len(scores), 1),
         'n': len(scores)}
        for name, scores in criteria_scores.items()
    ), key=lambda row: row['average'])

    credentials = db.session.query(
        func.count(MLSpecializationCredential.id)
    ).filter(
        MLSpecializationCredential.pathway_id == PATHWAY_ID,
        MLSpecializationCredential.revoked_at.is_(None),
    ).scalar() or 0

    return {
        'modules': modules,
        'enrolled': len(per_learner),
        'funnel': funnel,
        'attempts': attempt_rows,
        'criteria': criteria,
        'times': times,
        'credentials': credentials,
        'passed': {module_id: len({user for user, mid in passes if mid == module_id})
                   for module_id in module_ids},
    }


@admin_portal_bp.route('/analytics')
@admin_required
def analytics():
    since = _utcnow() - timedelta(days=30)
    completions = db.session.query(
        func.date(LessonCompletion.completed_at).label('date'),
        func.count(LessonCompletion.id).label('count'),
    ).filter(
        LessonCompletion.completed.is_(True),
        LessonCompletion.completed_at >= since,
    ).group_by(func.date(LessonCompletion.completed_at)).order_by(
        func.date(LessonCompletion.completed_at)
    ).all()
    signups = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count'),
    ).filter(User.created_at >= since).group_by(
        func.date(User.created_at)
    ).order_by(func.date(User.created_at)).all()
    module_counts = db.session.query(
        LessonCompletion.subject_id,
        func.count(LessonCompletion.id),
    ).filter(
        LessonCompletion.completed.is_(True)
    ).group_by(LessonCompletion.subject_id).all()
    module_lessons = {module['id']: {lesson['id'] for lesson in module['lessons']}
                      for module in all_modules()}
    learners_by_module = {}
    per_learner_module = db.session.query(
        LessonCompletion.user_id, LessonCompletion.subject_id,
        func.count(func.distinct(LessonCompletion.lesson_id)).label('lesson_count'),
    ).join(User, User.id == LessonCompletion.user_id).filter(
        LessonCompletion.completed.is_(True), User.is_active.is_(True),
        User.is_admin.is_(False),
    ).group_by(LessonCompletion.user_id, LessonCompletion.subject_id).all()
    for _learner_id, module_id, lesson_count in per_learner_module:
        module_stats = learners_by_module.setdefault(module_id, {
            'started': 0, 'finished': 0,
        })
        module_stats['started'] += 1
        total = len(module_lessons.get(module_id, ()))
        if total and lesson_count >= total:
            module_stats['finished'] += 1
    project_counts = dict(db.session.query(
        CourseProject.module_id, func.count(CourseProject.id),
    ).join(User, User.id == CourseProject.user_id).filter(
        CourseProject.completed.is_(True), User.is_active.is_(True),
        User.is_admin.is_(False),
    ).group_by(CourseProject.module_id).all())
    active_learners = User.query.filter(
        User.is_active.is_(True), User.is_admin.is_(False)
    ).count()
    module_funnel = []
    for module in all_modules():
        module_id = module['id']
        module_stats = learners_by_module.get(
            module_id, {'started': 0, 'finished': 0}
        )
        module_funnel.append({
            'number': module['number'], 'title': module['title'],
            'started': module_stats['started'], 'finished': module_stats['finished'],
            'projects': project_counts.get(module_id, 0),
        })
    quiz_summary = db.session.query(
        func.count(QuizResult.id), func.avg(QuizResult.score),
        func.sum(QuizResult.passed.cast(db.Integer)),
    ).filter(QuizResult.taken_at >= since).one()
    top_learners = db.session.query(
        User.id,
        User.username,
        User.email,
        func.count(LessonCompletion.id).label('completed'),
    ).join(
        LessonCompletion, LessonCompletion.user_id == User.id
    ).filter(
        LessonCompletion.completed.is_(True)
    ).group_by(User.id, User.username, User.email).order_by(
        func.count(LessonCompletion.id).desc()
    ).limit(10).all()
    return render_template(
        'admin/analytics.html',
        completions=completions,
        signups=signups,
        module_counts=module_counts,
        module_funnel=module_funnel,
        active_learners=active_learners,
        quiz_summary=quiz_summary,
        top_learners=top_learners,
        total_users=User.query.count(),
        active_accounts=User.query.filter(User.is_active.is_(True)).count(),
        since=since.date(),
        ml_pilot=_ml_pilot_snapshot(),
    )


@admin_portal_bp.route('/audit')
@admin_required
def audit_log():
    search = (request.args.get('q') or '').strip()
    action = request.args.get('action') or ''
    page = max(1, request.args.get('page', 1, type=int) or 1)

    query = AdminAuditLog.query
    if search:
        query = query.filter(AdminAuditLog.detail.ilike(f'%{search}%'))
    if action:
        query = query.filter(AdminAuditLog.action == action)

    pagination = query.order_by(
        AdminAuditLog.created_at.desc()
    ).paginate(page=page, per_page=PAGE_SIZE, error_out=False)

    related_ids = set()
    for entry in pagination.items:
        if entry.admin_user_id:
            related_ids.add(entry.admin_user_id)
        if entry.target_user_id:
            related_ids.add(entry.target_user_id)
    names = {}
    if related_ids:
        names = {
            account.id: _account_label(account)
            for account in User.query.filter(User.id.in_(related_ids)).all()
        }
    actions = [
        row[0] for row in db.session.query(
            AdminAuditLog.action
        ).distinct().order_by(AdminAuditLog.action).all()
    ]
    return render_template(
        'admin/audit.html',
        entries=pagination.items,
        pagination=pagination,
        names=names,
        actions=actions,
        search=search,
        action=action,
    )


@admin_portal_bp.route('/support')
@admin_required
def support_requests():
    status = (request.args.get('status') or '').strip()
    allowed_statuses = {'new', 'in_review', 'planned', 'resolved', 'declined'}
    query = SupportRequest.query.order_by(SupportRequest.created_at.desc())
    if status in allowed_statuses:
        query = query.filter_by(status=status)
    page = max(1, request.args.get('page', 1, type=int) or 1)
    pagination = query.paginate(page=page, per_page=PAGE_SIZE, error_out=False)
    return render_template(
        'admin/support.html', requests=pagination.items,
        pagination=pagination, status=status,
    )


@admin_portal_bp.route('/support/<int:request_id>', methods=['GET', 'POST'])
@admin_required
def support_request_detail(request_id):
    report = db.get_or_404(SupportRequest, request_id)
    if request.method == 'POST':
        status = (request.form.get('status') or '').strip()
        allowed_statuses = {'new', 'in_review', 'planned', 'resolved', 'declined'}
        reply = request.form.get('reply')
        if reply is not None:
            reply = reply.strip()[:4000]
            if not reply:
                flash('Write a reply before sending it.', 'error')
            else:
                report.admin_reply = reply
                report.replied_at = _utcnow()
                report.replied_by_user_id = current_user.id
                if status in allowed_statuses:
                    report.status = status
                report.updated_at = _utcnow()
                _record_admin_action(
                    'support.reply', target_user_id=report.user_id,
                    detail=f'Replied to support request #{report.id}.',
                )
                db.session.commit()
                flash('Reply saved and visible to the learner.', 'success')
                return redirect(url_for(
                    'admin_portal.support_request_detail', request_id=report.id
                ))
        elif status not in allowed_statuses:
            flash('Choose a valid status.', 'error')
        else:
            report.status = status
            report.updated_at = _utcnow()
            db.session.commit()
            flash('Support request updated.', 'success')
            return redirect(url_for(
                'admin_portal.support_request_detail', request_id=report.id
            ))
    return render_template('admin/support_detail.html', report=report)
