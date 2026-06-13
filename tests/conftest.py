"""Pytest bootstrap: ensure the project root is importable regardless of CWD."""

import sys
from pathlib import Path

# Prepend the project root (parent of the ai_rpa_system package) to sys.path
# so `import ai_rpa_system` works under pytest no matter where it's invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
