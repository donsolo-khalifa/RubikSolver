"""Shared helpers for the tools: make ``app`` importable and parse the camera source."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def parse_source(value: str | None):
    from app import config

    if value is None:
        return config.CAMERA_SOURCE
    return int(value) if value.isdigit() else value
