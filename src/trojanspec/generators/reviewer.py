"""Programmatic helpers for the human-review stage.

The interactive UI lives in ``scripts/03_review_triples.py``; this module
holds the reusable logic so it can be unit-tested without Streamlit.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from trojanspec.schemas import Triple


def load_triples(data_dir: Path) -> list[tuple[Path, Triple]]:
    """Load every ``*.json`` triple under ``data_dir``."""
    out: list[tuple[Path, Triple]] = []
    for f in sorted(data_dir.rglob("*.json")):
        out.append((f, Triple.model_validate_json(f.read_text())))
    return out


def unreviewed(pairs: list[tuple[Path, Triple]]) -> list[tuple[Path, Triple]]:
    return [(p, t) for p, t in pairs if t.reviewed_by is None]


def record_decision(
    triple: Triple, *, reviewer: str, accepted: bool, notes: str = ""
) -> Triple:
    """Stamp a review decision onto ``triple`` (does not write to disk)."""
    triple.reviewed_by = reviewer
    triple.review_passed = accepted
    triple.review_notes = notes or None
    triple.review_timestamp = datetime.now(timezone.utc)
    return triple


def save_triple(path: Path, triple: Triple) -> None:
    path.write_text(triple.model_dump_json(indent=2))
