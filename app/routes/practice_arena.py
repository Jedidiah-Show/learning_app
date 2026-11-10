"""RUACH Practice Arena routes."""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from app.practice import all_practice_exercises

practice_arena_bp = Blueprint('practice_arena', __name__)


@practice_arena_bp.route('/practice')
@login_required
def index():
    exercises = list(all_practice_exercises().values())
    return render_template('practice_arena/index.html', exercises=exercises)


@practice_arena_bp.route('/practice/ai-engineering')
@login_required
def ai_engineering():
    exercises = list(all_practice_exercises().values())
    return render_template('practice_arena/track.html', track='ai_engineering', track_name='AI Engineering Practice', exercises=exercises)


@practice_arena_bp.route('/practice/algorithms')
@login_required
def algorithms():
    exercises = list(all_practice_exercises().values())
    return render_template('practice_arena/track.html', track='algorithms', track_name='Algorithms & Problem Solving', exercises=exercises)


@practice_arena_bp.route('/practice/catalogue')
@login_required
def catalogue():
    exercises = list(all_practice_exercises().values())
    return render_template('practice_arena/catalogue.html', exercises=exercises)
