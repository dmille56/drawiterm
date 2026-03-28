"""File I/O: save/load .drawiterm JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from .models import Document

CURRENT_SCHEMA_VERSION = 1


def save(document: Document, path: Path) -> None:
    data = document.to_dict()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load(path: Path) -> Document:
    data = json.loads(path.read_text(encoding="utf-8"))
    version = data.get("schema_version", 1)
    data = _migrate(data, version)
    return Document.from_dict(data)


def _migrate(data: dict, from_version: int) -> dict:
    """Apply forward migrations from from_version to CURRENT_SCHEMA_VERSION."""
    # No migrations needed yet (only version 1 exists).
    return data
