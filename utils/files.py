from __future__ import annotations

import os
import re
from werkzeug.utils import secure_filename as _secure


def allowed_file(filename: str, allowed_extensions: tuple[str, ...]) -> bool:
    if not filename or "." not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    return ext in {e.lstrip(".") for e in allowed_extensions}


def secure_filename(filename: str) -> str:
    # Use Werkzeug then additionally normalize
    fname = _secure(filename)
    fname = re.sub(r"[^a-zA-Z0-9_.-]", "_", fname)
    return fname

