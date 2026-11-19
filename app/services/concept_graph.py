"""Concept graph bridging curriculum structure and competency records (M6.1).

Nodes:
- module nodes   ``sf.00`` / ``ai.03`` / ``mle.*``
- lesson nodes   lesson ids from the canonical manifests
- competency nodes — the free-text competency tags published on modules
  (e.g. ``llm``, ``statistics``). Where an arena/passport skill node shares
  the same id stem, the competency node references that skill id.

Edges:
- ``contains``     module → its lessons
- ``has_competency`` module → competency tag
- ``depends_on``   module → prerequisite module (cross-domain allowed only
  when Foundations is the source; enforced by the registry validator)

All curriculum edges come from the validated registry, so cross-specialisation
dependencies cannot leak into the graph.
"""

from app.curriculum_registry import registry

_EDGE_TYPES = ('contains', 'has_competency', 'depends_on')


def _skill_node_for(competency):
    """Map a competency tag onto a SkillNode id when a safe match exists."""
    import re
    slug = re.sub(r'[^a-z0-9]+', '-', (competency or '').strip().lower()).strip('-')
    return f'ml-{slug}' if slug else None


def build_graph(domain=None):
    """Return {'nodes': [...], 'edges': [...]} for one domain or all domains."""
    domains = [domain] if domain else registry.domain_ids()
    nodes, edges = [], []
    seen = set()

    def add_node(node):
        if node['id'] in seen:
            return
        seen.add(node['id'])
        nodes.append(node)

    for domain_id in domains:
        dom = registry.get_domain(domain_id)
        for module in dom.modules:
            add_node({'id': module['id'], 'type': 'module', 'domain': domain_id,
                      'title': module['title'], 'number': module['number']})
            for lesson in module['lessons']:
                add_node({'id': lesson['id'], 'type': 'lesson', 'domain': domain_id,
                          'title': lesson['title'], 'module_id': module['id']})
                edges.append({'source': module['id'], 'target': lesson['id'], 'type': 'contains'})
            for competency in module.get('competencies') or []:
                competency_id = f'concept:{competency}'
                add_node({'id': competency_id, 'type': 'concept', 'domain': domain_id,
                          'title': competency, 'skill_id': _skill_node_for(competency)})
                edges.append({'source': module['id'], 'target': competency_id,
                              'type': 'has_competency'})
            for prereq in module.get('prerequisites') or []:
                edges.append({'source': module['id'], 'target': prereq,
                              'type': 'depends_on'})
    return {'nodes': nodes, 'edges': edges}


def dependents_of(module_id):
    """All modules that depend on ``module_id`` (transitive)."""
    graph_domains = registry.domain_ids()
    reverse = {}
    for domain_id in graph_domains:
        for module in registry.get_domain(domain_id).modules:
            for prereq in module.get('prerequisites') or []:
                reverse.setdefault(prereq, set()).add(module['id'])
    ordered, queue = [], list(reverse.get(module_id, ()))
    visited = set(queue)
    while queue:
        current = queue.pop(0)
        ordered.append(current)
        for dependent in reverse.get(current, ()):
            if dependent not in visited:
                visited.add(dependent)
                queue.append(dependent)
    return ordered


def prerequisites_of(domain, module_id):
    """Depth-first prerequisite resolution through the canonical registry."""
    return registry.resolve_prerequisites(domain, module_id)


def is_valid_edge(source_domain, source_type, target_domain, target_type):
    """Allowed directed edges between curriculum graph levels."""
    if source_type == 'module' and target_type == 'module':
        # Only Foundations → specialisation edges (registry enforces at load).
        if source_domain == target_domain:
            return True
        return target_domain == 'shared-foundations' or source_domain == 'shared-foundations'
    return (source_type, target_type) in {
        ('module', 'lesson'), ('module', 'concept'),
    }
