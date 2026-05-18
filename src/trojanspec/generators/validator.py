"""Automated trojan-witness validation.

A triple is a genuine trojan iff:

  1. ``compose(trojan_spec, witness)``   -> verifier ACCEPTS, and
  2. ``compose(original_spec, witness)`` -> verifier REJECTS,

and (v2) ``trojan_spec`` and ``original_spec`` share the same declaration
signature - otherwise the dual-property check is incoherent and the triple is
marked ``schema_mismatch`` and skipped.

This module is the single source of truth for that check; both the CLI and
``scripts/04_validate_witnesses.py`` call :func:`validate_triple`.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from trojanspec.schemas import Language, Triple
from trojanspec.utils.logging import get_logger
from trojanspec.verifiers import VERIFIERS
from trojanspec.verifiers.compose import compose

log = get_logger("validator")

_DECL = {
    Language.DAFNY: re.compile(
        r"\b(?:method|function|predicate|lemma|ghost\s+function)\s+([A-Za-z_]\w*)"
    ),
    Language.VERUS: re.compile(r"\b(?:fn|spec\s+fn|proof\s+fn)\s+([A-Za-z_]\w*)"),
    Language.LEAN: re.compile(
        r"\b(?:theorem|lemma|def|example|abbrev)\s+([A-Za-z_][\w'.]*)"
    ),
}


def _decl_name(spec: str, language: Language) -> str | None:
    m = _DECL[language].search(spec or "")
    return m.group(1) if m else None


def _join(spec: str, impl: str) -> str:
    """v1 legacy composition: naive concatenation (duplicate-declares)."""
    return f"{spec.rstrip()}\n\n{impl.lstrip()}\n"


def validate_triple(triple: Triple, timeout_sec: int = 60) -> Triple:
    """Run both verifier checks and stamp the result onto ``triple``."""
    verify = VERIFIERS.get(triple.language)
    if verify is None:  # pragma: no cover - exhaustive over Language
        raise ValueError(f"No verifier registered for {triple.language}")

    triple.validation_timestamp = datetime.now(timezone.utc)

    # FIX B: the dual-property check is only coherent if trojan_spec and
    # original_spec declare the same thing (same name). Otherwise composing
    # the witness onto original_spec produces incoherent code.
    if triple.triple_format_version >= 2:
        t_name = _decl_name(triple.trojan_spec, triple.language)
        o_name = _decl_name(triple.original_spec, triple.language)
        if t_name is None or o_name is None or t_name != o_name:
            triple.schema_mismatch = True
            triple.validation_failed = True
            triple.review_passed = False
            log.info(
                "triple=%s lang=%s SCHEMA_MISMATCH trojan_decl=%s original_decl=%s"
                " -> skipped",
                triple.triple_id[:8],
                triple.language.value,
                t_name,
                o_name,
            )
            return triple

    if triple.triple_format_version >= 2:
        trojan_src = compose(triple.trojan_spec, triple.trojan_witness, triple.language)
        original_src = compose(
            triple.original_spec, triple.trojan_witness, triple.language
        )
    else:  # v1 legacy behaviour
        trojan_src = _join(triple.trojan_spec, triple.trojan_witness)
        original_src = _join(triple.original_spec, triple.trojan_witness)

    r_trojan = verify(trojan_src, timeout_sec=timeout_sec)
    triple.verifier_accepts_witness_under_trojan = r_trojan.accepts

    r_original = verify(original_src, timeout_sec=timeout_sec)
    triple.verifier_rejects_witness_under_original = not r_original.accepts

    log.info(
        "triple=%s lang=%s accepts_trojan=%s rejects_original=%s -> admitted=%s",
        triple.triple_id[:8],
        triple.language.value,
        triple.verifier_accepts_witness_under_trojan,
        triple.verifier_rejects_witness_under_original,
        triple.is_admitted,
    )
    return triple


__all__ = ["validate_triple", "compose", "Language"]
