"""Make the kit's own modules importable when pytest runs from any folder.

The kit's ``pyproject.toml`` already puts ``src`` on the path when pytest
uses it as the configuration file, which is what happens when you run
``pytest`` inside your own copy of this project. This file covers the case
where the checks are run from a parent folder, which happens when the kit
sits inside a larger repository.

The path is appended rather than prepended, so a reference implementation
placed earlier on ``PYTHONPATH`` still wins over the starter stub.
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))
