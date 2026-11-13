"""Make the kit's checks runnable straight from a checkout.

Two jobs, both small:

1. Put the kit's ``src`` directory on ``sys.path`` so ``import profile``
   works even when the package has not been installed.
2. When this kit lives inside the course repository, that repository also
   ships a finished reference implementation under ``tests/ml_reference``.
   If such a directory is on the path, the checks should run against it
   rather than against the stub in ``src``, so it is moved to the front.
"""

import sys
from pathlib import Path


KIT_ROOT = Path(__file__).resolve().parents[1]
SRC = str(KIT_ROOT / 'src')

if SRC not in sys.path:
    sys.path.insert(0, SRC)

for entry in list(sys.path):
    if entry.endswith('ml_reference'):
        sys.path.remove(entry)
        sys.path.insert(0, entry)
