"""Starter kit generation for shared course module projects.

Keeps starter-kit content out of route handlers so it can be tested and reused.
"""

from __future__ import annotations

from app.curriculum import get_module


# Module 0 delivers a glossary plus an architecture sketch, so it gets the docs
# kit; every later module gets a code kit shaped by its project brief.
STARTER_KITS = {
    '00': 'docs',
    '01': 'python-cli',
    '02': 'fastapi-service',
    '03': 'rag',
    '04': 'agent',
    '05': 'mcp',
    '06': 'evaluation-harness',
    '07': 'deploy',
    '08': 'mcp',
    '09': 'deploy',
    '10': 'deploy',
    '11': 'capstone',
    '12': 'capstone',
}
DEFAULT_STARTER_KIT = 'python-cli'


def module_starter_kit(module_id):
    module = get_module(module_id)
    key = module_id if module_id in STARTER_KITS else (
        f"{module.get('number'):02d}" if module else ''
    )
    return STARTER_KITS.get(key, DEFAULT_STARTER_KIT)


def starter_files(module_id):
    module = get_module(module_id) or {}
    number = module.get('number') or 0
    title = module.get('title') or 'Module project'
    project = module.get('project') or module.get('description') or ''
    deliverables = module.get('project_deliverables') or []
    kit_id = module_starter_kit(module_id)
    slug = ''.join(
        char.lower() if char.isalnum() else '-' for char in module_id
    ).strip('-')
    root = f'ruach-module-{slug}'

    setup_lines = [
        '# Module project setup',
        '',
        '## Start',
        '',
        '1. Install Python 3.11 or newer.',
        '2. Create and activate a virtual environment.',
        '3. Install the development dependency with `python -m pip install -e .`.',
        '4. Run `pytest`.',
        '5. Replace the starter code with your project, then add tests for each requirement.',
        '',
        '## Publish',
        '',
        '1. `git init` (skip if the folder is already a repository).',
        '2. `git add -A && git commit -m "module project"`.',
        '3. `gh repo create <your-github-user>/<repo-name> --public --source . --remote origin --push`.',
        '4. Enable GitHub Actions for the new repository.',
        '5. Copy your automated-checks run URL into the course submission.',
        '',
        '## Verify',
        '',
        'Run the repository checks locally before publishing. The course submission requires a public repository and a public automated-checks page showing a successful build.',
    ]
    setup_md = '\n'.join(setup_lines) + '\n'

    readme_lines = [
        f'# Module {number}: {title}',
        '',
        '## Project brief',
        '',
        project,
        '',
        '## Start locally',
        '',
        '1. Install Python 3.11 or newer.',
        '2. Create and activate a virtual environment.',
        '3. Install the development dependency with `python -m pip install -e .`.',
        '4. Run `pytest`.',
        '5. Replace the starter with your project, then add tests for each requirement.',
        '',
    ]
    for index, deliverable in enumerate(deliverables, start=1):
        readme_lines.append(f'{index}. Deliverable: {deliverable}')
    readme_lines += [
        '',
        'Keep credentials out of this repository. Add a README section describing setup, decisions, limitations, and evidence. The course submission still asks for a public repository, passing automated checks, and the project evaluation.',
    ]
    readme = '\n'.join(readme_lines) + '\n'

    pyproject = '[build-system]\nrequires = ["setuptools>=68"]\nbuild-backend = "setuptools.build_meta"\n\n[project]\nname = "ruach-module-starter"\nversion = "0.1.0"\nrequires-python = ">=3.11"\ndependencies = []\n\n[project.optional-dependencies]\ndev = ["pytest>=8"]\n\n[tool.pytest.ini_options]\npythonpath = ["src"]\n'
    gitignore = '.venv/\n__pycache__/\n.pytest_cache/\n*.py[cod]\n.env\n'
    ci = 'name: tests\non:\n  push:\n  pull_request:\njobs:\n  pytest:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with:\n          python-version: "3.11"\n      - run: python -m pip install -e ".[dev]"\n      - run: pytest\n'
    src_main = '"""Start here: replace this starter with the module project."""\n\n\ndef main() -> str:\n    return "Implement the project described in README.md"\n\n\nif __name__ == "__main__":\n    print(main())\n'
    test_main = 'from main import main\n\n\ndef test_main_returns_a_string():\n    assert isinstance(main(), str)\n'

    files = {}
    if kit_id == 'docs':
        files[f'{root}/README.md'] = readme
        files[f'{root}/SETUP.md'] = setup_md
        files[f'{root}/pyproject.toml'] = pyproject
        files[f'{root}/.gitignore'] = gitignore
        files[f'{root}/.github/workflows/docs.yml'] = (
            'name: docs\non:\n  push:\n  pull_request:\njobs:\n  docs:\n'
            '    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n'
            '      - uses: actions/setup-python@v5\n        with:\n          python-version: "3.11"\n'
            '      - run: python -m pytest tests/test_docs.py\n'
        )
        files[f'{root}/tests/test_docs.py'] = (
            '"""Starter kit checks for the module documentation deliverable."""\n\n'
            'from pathlib import Path\n\n'
            'def test_glossary_is_present():\n    glossary = (  # noqa: SIM108\n'
            '        Path(__file__).parent.parent / "docs" / "glossary.md"\n    ).read_text()\n    assert glossary.strip()\n\n\n'
            'def test_architecture_sketch_is_present():\n    sketch = (\n'
            '        Path(__file__).parent.parent / "docs" / "architecture-sketch.md"\n    ).read_text()\n    assert sketch.strip()\n'
        )
        files[f'{root}/docs/glossary.md'] = (
            f'# Module {number} glossary\n\n## Key terms\n\n- {title}: the subject of this module.\n'
        )
        files[f'{root}/docs/architecture-sketch.md'] = (
            f'# Module {number} architecture sketch\n\n'
            '## System sketch\n\nDescribe the request, data, tool, application, and operations boundaries for the module project.\n'
        )
    else:
        files[f'{root}/README.md'] = readme
        files[f'{root}/SETUP.md'] = setup_md
        files[f'{root}/pyproject.toml'] = pyproject
        files[f'{root}/.gitignore'] = gitignore
        files[f'{root}/.github/workflows/tests.yml'] = ci
        files[f'{root}/src/main.py'] = src_main
        files[f'{root}/tests/test_main.py'] = test_main
    return files
