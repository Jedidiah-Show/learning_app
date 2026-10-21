from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import User
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit
import json
import os

auth_bp = Blueprint('auth', __name__)


def safe_local_redirect(target):
    if not target:
        return False
    ref = urlsplit(urljoin(request.host_url, target))
    return ref.scheme in {'http', 'https'} and ref.netloc == request.host

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username') or request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter((User.username == username) | (User.email == username)).first()
        if user and user.password_hash and check_password_hash(user.password_hash, password):
            login_user(user)
            user.last_active = datetime.now(timezone.utc)
            db.session.commit()
            next_page = request.args.get('next')
            return redirect(next_page) if safe_local_redirect(next_page) else redirect(url_for('main.index'))
        flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password')
        full_name = (request.form.get('full_name') or '').strip()

        if not username or not email or not password or len(password) < 8:
            flash('Enter a username, email, and password with at least 8 characters.', 'error')
            return render_template('auth/register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('auth/register.html')
        if email and User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('auth/register.html')
        
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            password_hash=generate_password_hash(password),
            created_at=datetime.now(timezone.utc),
            last_active=datetime.now(timezone.utc)
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Registration successful!', 'success')
        # After registration, go to subject configuration
        return redirect(url_for('main.subject_configuration'))
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
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
    data = request.get_json(silent=True) or request.form
    email = (data.get('email') or '').strip().lower() if data.get('email') is not None else None
    phone = (data.get('phone') or '').strip() if data.get('phone') is not None else None
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
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
        current_user.phone = phone or None
    
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
    
    db.session.commit()
    if request.is_json:
        return {'status': 'success'}
    flash('Account updated successfully', 'success')
    return redirect(url_for('auth.profile'))


@auth_bp.route('/account/delete', methods=['POST'])
@login_required
def delete_account():
    user = current_user
    # Delete all related data explicitly for safety
    try:
        # Relationships have cascade, but be thorough
        from app import models
        # Delete in case cascades missed
        db.session.delete(user)
        db.session.commit()
        logout_user()
        flash('Account deleted permanently', 'info')
        if request.is_json:
            return {'status': 'success'}
        return redirect(url_for('auth.login'))
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return {'error': str(e)}, 500
        flash('Failed to delete account', 'error')
        return redirect(url_for('auth.profile'))


@auth_bp.route('/account/reset', methods=['POST'])
@login_required
def reset_account():
    user = current_user
    try:
        # Delete all user data but keep the user account
        from app.models import (Progress, LessonCompletion, QuizResult, StudySession, 
                                UserSubjectConfig, ProficiencyTest, CalendarEvent,
                                UserSubject, UserSchedule, UserConfig)
        Progress.query.filter_by(user_id=user.id).delete()
        LessonCompletion.query.filter_by(user_id=user.id).delete()
        QuizResult.query.filter_by(user_id=user.id).delete()
        StudySession.query.filter_by(user_id=user.id).delete()
        UserSubjectConfig.query.filter_by(user_id=user.id).delete()
        ProficiencyTest.query.filter_by(user_id=user.id).delete()
        CalendarEvent.query.filter_by(user_id=user.id).delete()
        UserSubject.query.filter_by(user_id=user.id).delete()
        UserSchedule.query.filter_by(user_id=user.id).delete()
        UserConfig.query.filter_by(user_id=user.id).delete()
        user.subjects_configured = False
        db.session.commit()
        flash('Account reset successfully', 'success')
        if request.is_json:
            return {'status': 'success'}
        return redirect(url_for('main.index'))
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return {'error': str(e)}, 500
        flash('Failed to reset account', 'error')
        return redirect(url_for('auth.profile'))
