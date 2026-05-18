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
    """v1 legacy composition: naive concatenation (duplicate-declares)."""
    return f"{spec.rstrip()}\n\n{impl.lstrip()}\n"


def _first_brace_block(text: str) -> str | None:
    """Return the first balanced ``{...}`` block (inclusive), or None."""
    i = text.find("{")
    if i == -1:
        return None
    depth = 0
    for j in range(i, len(text)):
        c = text[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[i : j + 1]
    return None


def compose(contract: str, witness: str, language: Language) -> str:
    """v2 composition: the witness BODY under the given CONTRACT.

    The contract supplies the signature + pre/post (any stray body in the
    contract is dropped); the witness supplies the implementation. The result
    is a single well-formed program - no duplicate declarations.
    """
    contract = contract.strip()
    witness = witness.strip()

    if language is Language.LEAN:
        # statement = contract up to (not incl) its first ':='; proof = the
        # witness's ':= ...' tail.
        stmt = contract.split(":=", 1)[0].rstrip()
        if ":=" in witness:
            proof = ":=" + witness.split(":=", 1)[1]
            return f"{stmt} {proof.strip()}\n"
        # No proof in the witness -> leave it to fail honestly.
        return f"{stmt}\n{witness}\n"

    # Dafny / Verus: header = contract before its first body block; body =
    # the witness's first balanced { ... } block.
    cbrace = contract.find("{")
    header = (contract[:cbrace] if cbrace != -1 else contract).rstrip()
    body = _first_brace_block(witness)
    if body is None:
        return f"{header}\n{witness}\n"
    return f"{header}\n{body}\n"


def validate_triple(triple: Triple, timeout_sec: int = 60) -> Triple:
    """Run both verifier checks and stamp the result onto ``triple``."""
    verify = VERIFIERS.get(triple.language)
    if verify is None:  # pragma: no cover - exhaustive over Language
        raise ValueError(f"No verifier registered for {triple.language}")

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
