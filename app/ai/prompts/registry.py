"""Versioned prompt registry (M2.5).

Version metadata lives in a bundled JSON catalogue so it is reviewable in git.
Rollback is an application-level override of the active version, which lets an
operator select a previously approved version without editing template files.
"""

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from flask import current_app, has_app_context


_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'templates', 'prompts.json')
_OVERRIDE_CONFIG_KEY = 'AI_PROMPT_VERSION_OVERRIDES'


@dataclass(frozen=True)
class PromptVersion:
    key: str
    version: str
    metadata: Dict[str, Any]

    @property
    def template(self) -> Optional[str]:
        return self.metadata.get('template')

    def render(self, **variables: Any) -> str:
        if not isinstance(self.template, str):
            raise ValueError(
                f'Prompt {self.key}@{self.version} has no renderable template'
            )
        try:
            return self.template.format(**variables)
        except KeyError as error:
            raise ValueError(
                f'Missing prompt variable {error.args[0]!r} for {self.key}@{self.version}'
            ) from error


def _catalogue() -> Dict[str, Any]:
    with open(_TEMPLATE_PATH, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def list_prompts() -> Dict[str, Dict[str, Any]]:
    """Return catalogue metadata with the currently active version resolved."""
    catalogue = _catalogue()
    return {
        key: {
            'active': active_version(key),
            'versions': [
                {**item, 'key': key}
                for item in definition.get('versions', [])
            ],
        }
        for key, definition in catalogue.items()
    }


def _overrides() -> Dict[str, str]:
    if not has_app_context():
        return {}
    overrides = current_app.config.get(_OVERRIDE_CONFIG_KEY) or {}
    return overrides if isinstance(overrides, dict) else {}


def active_version(key: str) -> str:
    catalogue = _catalogue()
    if key not in catalogue:
        raise ValueError(f'Unknown prompt key: {key}')
    override = _overrides().get(key)
    versions = {item['version'] for item in catalogue[key].get('versions', [])}
    if override in versions:
        return override
    return catalogue[key]['active']


def get_prompt(key: str, version: Optional[str] = None) -> PromptVersion:
    catalogue = _catalogue()
    if key not in catalogue:
        raise ValueError(f'Unknown prompt key: {key}')
    selected = version or active_version(key)
    for item in catalogue[key].get('versions', []):
        if item.get('version') == selected:
            return PromptVersion(key=key, version=selected, metadata=item)
    raise ValueError(f'Unknown prompt version {selected!r} for {key}')


def rollback(key: str, version: str) -> str:
    """Select a previously approved version for the current process."""
    get_prompt(key, version)
    if not has_app_context():
        raise RuntimeError('Prompt rollback requires an application context')
    overrides = dict(_overrides())
    overrides[key] = version
    current_app.config[_OVERRIDE_CONFIG_KEY] = overrides
    return version
