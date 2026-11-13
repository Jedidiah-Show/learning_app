"""Derived, stateless notifications for the learner shell.

Notifications are computed on every request from data the app already holds,
so there is no delivery queue, no read-state table and nothing to migrate.
Everything here is best-effort: a database hiccup must never take the shell
down, matching the tolerance of the pathway and review-badge reads.
"""

from datetime import date, datetime, timezone

from flask import url_for
from flask_login import current_user


def _module_title_map():
    titles = {}
    try:
        from app.curriculum import all_modules
        for module in all_modules():
            titles[module['id']] = module['title']
    except Exception:
        pass
    try:
        from app.ml_pathway import machine_learning_pathway
        for module in machine_learning_pathway().get('modules', []):
            titles.setdefault(module['id'], module['title'])
    except Exception:
        pass
    return titles


def build_notifications(user):
    """Return the learner's notification items, newest-action first.

    Every item is a dict with ``icon``, ``title``, ``body``, ``url`` and
    ``tone`` (``info`` | ``warn`` | ``success``). Admins get an empty list,
    matching how the streak and review badges behave in the nav shell.
    """
    if (
        not getattr(user, 'is_authenticated', False)
        or getattr(user, 'is_admin', False)
    ):
        return []
    items = []
    try:
        from app.models import (
            CourseProject, ReviewItem, SupportRequest,
        )

        now = datetime.now(timezone.utc)

        # Review Center: spaced repetition decays when answers are late.
        due = (
            ReviewItem.query
            .filter_by(user_id=user.id, active=True)
            .filter(ReviewItem.due_at <= now)
            .count()
        )
        if due:
            items.append({
                'icon': '🧠',
                'title': f'{due} card{"s" if due != 1 else ""} due for review',
                'body': 'Spaced repetition only works when each answer is on time.',
                'url': url_for('main.review'),
                'tone': 'info',
            })

        # Streak: keeping it alive is a once-a-day commitment.
        streak = getattr(user, 'streak', 0) or 0
        last_study = getattr(user, 'last_study_date', None)
        if streak >= 1 and (last_study is None or last_study < date.today()):
            items.append({
                'icon': '🔥',
                'title': f'Your {streak}-day streak is on the line',
                'body': 'Finish a lesson, quiz or review today to keep it alive.',
                'url': url_for('main.lessons'),
                'tone': 'warn',
            })

        # Support: at most the three most recent replied reports.
        replies = (
            SupportRequest.query
            .filter(
                SupportRequest.user_id == user.id,
                SupportRequest.admin_reply.isnot(None),
            )
            .order_by(SupportRequest.updated_at.desc())
            .limit(3)
            .all()
        )
        if replies:
            latest = replies[0]
            extra = f' (+{len(replies) - 1} more)' if len(replies) > 1 else ''
            items.append({
                'icon': '🛠️',
                'title': f'Support replied to “{latest.subject[:64]}”{extra}',
                'body': 'Open Tech Support & Ideas to read the reply.',
                'url': url_for('main.support'),
                'tone': 'info',
            })

        projects_url = url_for('projects.project_page')
        titles = _module_title_map()

        def module_label(module_id):
            return titles.get(module_id, f'Module {module_id}')

        # Public checks verified but the AI review has not run/finished yet.
        verified = (
            CourseProject.query
            .filter(
                CourseProject.user_id == user.id,
                CourseProject.checks_verified.is_(True),
                CourseProject.evaluation.is_(None),
                CourseProject.completed.is_(False),
            )
            .order_by(CourseProject.updated_at.desc())
            .first()
        )
        if verified:
            items.append({
                'icon': '✅',
                'title': 'Automated checks verified',
                'body': f'The checks for {module_label(verified.module_id)} are green. '
                        'AI review runs next — the verdict will appear on Projects.',
                'url': f'{projects_url}#module-{verified.module_id}',
                'tone': 'success',
            })

        # AI evaluation written but the module project is not marked complete:
        # the learner still owes a read of the rubric feedback.
        evaluated = (
            CourseProject.query
            .filter(
                CourseProject.user_id == user.id,
                CourseProject.evaluation.isnot(None),
                CourseProject.completed.is_(False),
            )
            .order_by(CourseProject.updated_at.desc())
            .first()
        )
        if evaluated:
            items.append({
                'icon': '🧩',
                'title': 'AI feedback is ready',
                'body': f'Your {module_label(evaluated.module_id)} project has been '
                        'evaluated — open Projects to read the rubric notes.',
                'url': f'{projects_url}#module-{evaluated.module_id}',
                'tone': 'success',
            })
    except Exception:
        from flask import current_app
        current_app.logger.exception('Could not build notifications')
        return []
    return items
