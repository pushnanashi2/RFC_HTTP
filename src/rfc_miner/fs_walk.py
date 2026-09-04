from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


def iter_files(root: Path, ignored_dirs: set[str]) -> Iterable[Path]:
    for directory, dirnames, filenames in os.walk(root, topdown=True, onerror=lambda _error: None):
        dirnames[:] = [name for name in dirnames if name not in ignored_dirs]
        current = Path(directory)
        for filename in filenames:
            yield current / filename
