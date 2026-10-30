"""Authenticated learner discussion space."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import CommunityPost, CommunityReply, utcnow
from app.rate_limit import enforce_rate_limit


community_bp = Blueprint('community', __name__)
TOPICS = (
    'General', 'LLM APIs', 'Prompt evaluation', 'RAG',
    'Agents and MCP', 'Production and deployment', 'Project feedback',
)


@community_bp.route('/community')
@login_required
def index():
    topic = request.args.get('topic', '').strip()
    if topic and topic not in TOPICS:
        topic = ''
    query = CommunityPost.query
    if topic:
        query = query.filter_by(topic=topic)
    posts = query.order_by(CommunityPost.updated_at.desc(), CommunityPost.id.desc()).paginate(
        page=request.args.get('page', 1, type=int), per_page=20, error_out=False
    )
    post_ids = [post.id for post in posts.items]
    counts = dict(db.session.query(
        CommunityReply.post_id, db.func.count(CommunityReply.id)
    ).filter(CommunityReply.post_id.in_(post_ids)).group_by(
        CommunityReply.post_id
    ).all()) if post_ids else {}
    return render_template(
        'community.html', posts=posts, topics=TOPICS, selected_topic=topic,
        reply_counts=counts,
    )


@community_bp.route('/community/posts', methods=['POST'])
@login_required
def create_post():
    enforce_rate_limit('community-post', 5, 3600, str(current_user.id))
    topic = request.form.get('topic', '').strip()
    title = request.form.get('title', '').strip()
    body = request.form.get('body', '').strip()
    if topic not in TOPICS:
        flash('Choose a discussion topic.', 'error')
        return redirect(url_for('community.index'))
    if not title or len(title) > 140:
        flash('Discussion titles must be 1–140 characters.', 'error')
        return redirect(url_for('community.index'))
    if not body or len(body) > 5000:
        flash('Discussion details must be 1–5000 characters.', 'error')
        return redirect(url_for('community.index'))
    post = CommunityPost(
        user_id=current_user.id, topic=topic, title=title, body=body,
    )
    db.session.add(post)
    db.session.commit()
    return redirect(url_for('community.discussion', post_id=post.id))


@community_bp.route('/community/posts/<int:post_id>')
@login_required
def discussion(post_id):
    post = db.get_or_404(CommunityPost, post_id)
    replies = CommunityReply.query.filter_by(post_id=post.id).order_by(
        CommunityReply.created_at.asc(), CommunityReply.id.asc()
    ).paginate(
        page=request.args.get('page', 1, type=int), per_page=50, error_out=False
    )
    return render_template('community_discussion.html', post=post, replies=replies)


@community_bp.route('/community/posts/<int:post_id>/replies', methods=['POST'])
@login_required
def create_reply(post_id):
    enforce_rate_limit('community-reply', 20, 3600, str(current_user.id))
    post = db.get_or_404(CommunityPost, post_id)
    body = request.form.get('body', '').strip()
    if not body or len(body) > 3000:
        flash('Replies must be 1–3000 characters.', 'error')
        return redirect(url_for('community.discussion', post_id=post.id))
    db.session.add(CommunityReply(
        post_id=post.id, user_id=current_user.id, body=body,
    ))
    post.updated_at = utcnow()
    db.session.commit()
    return redirect(url_for('community.discussion', post_id=post.id))


@community_bp.route('/community/posts/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = db.get_or_404(CommunityPost, post_id)
    if post.user_id != current_user.id and not current_user.is_admin:
        abort(403, description='Only the author or an administrator can remove this discussion.')
    db.session.delete(post)
    db.session.commit()
    flash('Discussion removed.', 'success')
    return redirect(url_for('community.index'))


@community_bp.route('/community/replies/<int:reply_id>/delete', methods=['POST'])
@login_required
def delete_reply(reply_id):
    reply = db.get_or_404(CommunityReply, reply_id)
    if reply.user_id != current_user.id and not current_user.is_admin:
        abort(403, description='Only the author or an administrator can remove this reply.')
    post_id = reply.post_id
    db.session.delete(reply)
    db.session.commit()
    flash('Reply removed.', 'success')
    return redirect(url_for('community.discussion', post_id=post_id))
