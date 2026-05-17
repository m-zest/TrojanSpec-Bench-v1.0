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


def apply_edits(triple: Triple, *, trojan_spec: str, trojan_witness: str) -> Triple:
    """Overwrite the trojan fields with reviewer-edited text (no disk write)."""
    triple.trojan_spec = trojan_spec
    triple.trojan_witness = trojan_witness
    return triple


def summary_counts(pairs: list[tuple[Path, Triple]]) -> tuple[int, int, int]:
    """Return ``(reviewed, total, accepted)`` across ``pairs``."""
    total = len(pairs)
    reviewed = sum(1 for _, t in pairs if t.reviewed_by is not None)
    accepted = sum(1 for _, t in pairs if t.review_passed)
    return reviewed, total, accepted


def filter_pairs(
    pairs: list[tuple[Path, Triple]],
    *,
    language: str | None = None,
    attack: str | None = None,
    difficulty: str | None = None,
    unreviewed_only: bool = False,
) -> list[tuple[Path, Triple]]:
    """Sidebar filter. ``None`` / falsy means "any" for that facet."""
    out = []
    for p, t in pairs:
        if language and t.language.value != language:
            continue
        if attack and t.attack_pattern.value != attack:
            continue
        if difficulty and t.difficulty.value != difficulty:
            continue
        if unreviewed_only and t.reviewed_by is not None:
            continue
        out.append((p, t))
    return out


def save_triple(path: Path, triple: Triple) -> None:
    path.write_text(triple.model_dump_json(indent=2))
