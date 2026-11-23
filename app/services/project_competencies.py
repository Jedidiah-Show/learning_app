"""Competency mapping for verified project evidence (M4).

Competencies come from published manifests, not from lesson completion:
- AI Engineering uses each module's ``competencies`` list, with stable ids.
- Machine Learning uses the existing ``ML_PROJECT_COMPETENCIES`` map.

A project never credits competencies from the other specialization.
"""

from __future__ import annotations

import re


def _slug(value):
    return re.sub(r'[^a-z0-9]+', '-', str(value).strip().lower()).strip('-')[:64]


def domain_is_supported(domain):
    return domain in ('ai-engineering', 'machine-learning')


def project_title(domain, project_key):
    if domain == 'ai-engineering':
        from app.ai_pathway import ai_engineering_pathway
        module = next(
            (m for m in ai_engineering_pathway()['modules'] if m['id'] == project_key),
            None,
        )
        return (module or {}).get('project_title') or (module or {}).get('title') or project_key
    if domain == 'machine-learning':
        from app.ml_pathway import machine_learning_pathway
        module = next(
            (m for m in machine_learning_pathway()['modules'] if m['id'] == project_key),
            None,
        )
        return (module or {}).get('title') or project_key
    return project_key


def competencies_for(domain, project_key):
    """Return ``[{'id', 'title', 'category'}]`` for a specialization project."""
    if not domain_is_supported(domain):
        raise ValueError(f'Unsupported project domain {domain!r}')
    if not isinstance(project_key, str) or not project_key.strip():
        raise ValueError('project_key is required')

    if domain == 'ai-engineering':
        from app.ai_pathway import ai_engineering_pathway
        module = next(
            (m for m in ai_engineering_pathway()['modules'] if m['id'] == project_key),
            None,
        )
        if module is None:
            raise ValueError(f'Unknown AI Engineering project {project_key!r}')
        result = []
        for raw in module.get('competencies') or []:
            title = str(raw).strip()
            if not title:
                continue
            result.append({
                'id': f'ai-competency-{_slug(title)}'[:64],
                'title': title[:128],
                'category': 'AI Engineering',
            })
        return result

    from app.ml_pathway import machine_learning_pathway
    from app.services.skill_passport import ML_COMPETENCIES, ML_PROJECT_COMPETENCIES

    if not any(m['id'] == project_key for m in machine_learning_pathway()['modules']):
        raise ValueError(f'Unknown Machine Learning project {project_key!r}')
    result = []
    for skill_id in ML_PROJECT_COMPETENCIES.get(project_key, ()):
        values = ML_COMPETENCIES.get(skill_id, {})
        result.append({
            'id': skill_id,
            'title': values.get('title') or skill_id.replace('-', ' ').title(),
            'category': values.get('category') or 'Machine Learning',
        })
    return result


__all__ = ['competencies_for', 'domain_is_supported', 'project_title']
