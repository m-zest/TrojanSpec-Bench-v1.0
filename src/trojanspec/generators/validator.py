"""Automated trojan-witness validation.

A triple is a genuine trojan iff:

  1. ``trojan_spec + trojan_witness``     -> verifier ACCEPTS, and
  2. ``original_spec + trojan_witness``   -> verifier REJECTS.

This module is the single source of truth for that check; both the CLI and
``scripts/04_validate_witnesses.py`` call :func:`validate_triple`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from trojanspec.schemas import Language, Triple
from trojanspec.utils.logging import get_logger
from trojanspec.verifiers import VERIFIERS

log = get_logger("validator")


def _join(spec: str, impl: str) -> str:
    return f"{spec.rstrip()}\n\n{impl.lstrip()}\n"


def validate_triple(triple: Triple, timeout_sec: int = 60) -> Triple:
    """Run both verifier checks and stamp the result onto ``triple``."""
    verify = VERIFIERS.get(triple.language)
    if verify is None:  # pragma: no cover - exhaustive over Language
        raise ValueError(f"No verifier registered for {triple.language}")

    r_trojan = verify(_join(triple.trojan_spec, triple.trojan_witness), timeout_sec=timeout_sec)
    triple.verifier_accepts_witness_under_trojan = r_trojan.accepts

    r_original = verify(
        _join(triple.original_spec, triple.trojan_witness), timeout_sec=timeout_sec
    )
    triple.verifier_rejects_witness_under_original = not r_original.accepts

    triple.validation_timestamp = datetime.now(timezone.utc)

    log.info(
        "triple=%s lang=%s accepts_trojan=%s rejects_original=%s -> admitted=%s",
        triple.triple_id[:8],
        triple.language.value,
        triple.verifier_accepts_witness_under_trojan,
        triple.verifier_rejects_witness_under_original,
        triple.is_admitted,
    )
    return triple


__all__ = ["validate_triple", "Language"]
