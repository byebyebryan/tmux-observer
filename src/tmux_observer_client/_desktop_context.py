"""Captured desktop endpoint incarnation; no compositor implementation imports."""

import os
from pathlib import Path


def context_fingerprint(context_id):
    path = os.environ.get("NIRI_SOCKET", "")
    try:
        stat = Path(path).stat() if path else None
        identity = (stat.st_dev, stat.st_ino) if stat else None
    except OSError:
        identity = None
    return context_id, path, identity
