"""File I/O: save/load .drawiterm JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from .models import SCHEMA_VERSION, Document


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
    if from_version < SCHEMA_VERSION:
        elements = data.get("elements", [])
        for element in elements:
            if element.get("element_type") == "arrow":
                element.setdefault("start_anchor", None)
                element.setdefault("end_anchor", None)
        data["schema_version"] = SCHEMA_VERSION
    return data
