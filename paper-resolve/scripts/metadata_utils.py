"""Shared utilities for paper metadata YAML operations."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def load_metadata(path: Path) -> dict[str, Any]:
    """Load a YAML metadata file and return as dict."""
    import yaml

    with open(path) as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def write_metadata(path: Path, data: dict[str, Any]) -> None:
    """Write dict to a YAML metadata file."""
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug.

    Lowercase, replace spaces/special chars with hyphens, collapse multiples.
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def find_existing_import(papers_dir: Path, identifier: str) -> Path | None:
    """Scan papers_dir for an existing bundle whose metadata matches identifier.

    Matches against title, DOI, or arXiv id in metadata.yaml.
    """
    if not papers_dir.exists():
        return None

    identifier_lower = identifier.lower()

    for child in papers_dir.iterdir():
        if not child.is_dir():
            continue
        metadata_path = child / "metadata.yaml"
        if not metadata_path.is_file():
            continue
        try:
            meta = load_metadata(metadata_path)
        except Exception:
            continue

        title = (meta.get("title") or "").lower()
        if identifier_lower in title:
            return child

        aliases = meta.get("identity", {}).get("aliases", {})
        for val in aliases.values():
            if val and str(val).lower() == identifier_lower:
                return child

    return None
