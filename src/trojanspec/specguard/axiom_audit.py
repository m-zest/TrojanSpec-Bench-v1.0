"""Axiom-audit detector (all three languages).

Flags ``implementation_leak``-style unverified surface (axiom-like
declarations whose postcondition the verifier accepts on faith) in the
*trojan-side composition* (``preamble + trojan_spec``) that the honest
``original_spec`` does not introduce.

Per-language signals:

  - Lean : ``axiom <name>``, ``opaque <name>``
  - Dafny: ``{:axiom}``, ``{:extern}``, ``{:verify false}``
  - Verus: ``#[verifier::external_body]``, ``#[verifier::external]``,
           ``#[verifier::assume_specification]``,
           an uninterpreted ``spec fn name(...) -> T;``
           (declaration body absent - the v4 implementation_leak
           pattern that the witness later discharges via ``assume(...)`` or
           an ``external_body proof fn`` axiom).

A signal in the trojan side that is **not** present in the honest
``original_spec`` is the diff worth flagging: an honest crypto-anchor seed
does not need axiomatic escape hatches, so any axiom-like construct
introduced by the trojan-side is the implementation-leak fingerprint. The
``preamble`` is identical across the trojan and original *compositions* but
is checked here on the trojan side specifically because the v4 deterministic
Lean leak repair places its axioms there - the original_spec (compared
against) never references them.

The pre-v4 detector was Lean-only and inspected ``trojan_spec`` only, so it
hit 0/1024 in Phase 9: it missed every Dafny ``{:axiom}`` triple by language
scope, every Verus ``external_body`` triple by language scope, and every
Lean deterministic-repair triple because the leak axioms live in
``preamble``. The phase9_followup_axiom_audit re-eval quantifies the lift.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from trojanspec.specguard.base import Detector, DetectorResult, Triple, Verdict

# (label, compiled regex). Order is purely cosmetic; verdict is set-based.
_PATTERNS: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    "lean": [
        ("axiom", re.compile(r"\baxiom\s+([A-Za-z_][\w'.]*)")),
        ("opaque", re.compile(r"\bopaque\s+([A-Za-z_][\w'.]*)")),
    ],
    "dafny": [
        # The attribute itself is the signal - capture the immediate decl
        # name when one is present, fall back to the attribute literal.
        ("{:axiom}",
         re.compile(r"\{:axiom\}\s*(?:function|predicate|method|lemma)?\s*([A-Za-z_]\w*)?")),
        ("{:extern}",
         re.compile(r"\{:extern\}\s*(?:function|predicate|method|lemma)?\s*([A-Za-z_]\w*)?")),
        ("{:verify false}",
         re.compile(r"\{:verify\s+false\}\s*(?:function|predicate|method|lemma)?\s*([A-Za-z_]\w*)?")),
    ],
    "verus": [
        ("external_body",
         re.compile(r"#\[verifier::external_body\]\s*(?:pub\s+)?(?:spec\s+|proof\s+|exec\s+)?fn\s+([A-Za-z_]\w*)")),
        ("external",
         re.compile(r"#\[verifier::external\]\s*(?:pub\s+)?(?:spec\s+|proof\s+|exec\s+)?fn\s+([A-Za-z_]\w*)")),
        ("assume_specification",
         re.compile(r"#\[verifier::assume_specification\]\s*(?:pub\s+)?(?:spec\s+|proof\s+|exec\s+)?fn\s+([A-Za-z_]\w*)")),
        # Uninterpreted spec fn: `spec fn name(args) -> T;` (no body block).
        # The trailing `;` (not `{`) distinguishes it from a defined spec fn.
        ("uninterpreted_spec_fn",
         re.compile(r"\bspec\s+fn\s+([A-Za-z_]\w*)\s*\([^)]*\)\s*->\s*[^{;]+;", re.M)),
    ],
}


def _findings(text: str, patterns: Iterable[tuple[str, re.Pattern[str]]]) -> set[str]:
    """Return {label or label:name} tokens for each pattern match."""
    out: set[str] = set()
    for label, pat in patterns:
        for m in pat.finditer(text or ""):
            name = (m.group(1) or "") if m.groups() else ""
            out.add(f"{label}:{name}" if name else label)
    return out


class AxiomAuditDetector(Detector):
    name = "axiom_audit"
    # language-agnostic: per-language pattern table dispatches internally.
    languages = None

    def scan(self, triple: Triple) -> DetectorResult:
        lang = (triple.get("language") or "").lower()
        patterns = _PATTERNS.get(lang)
        if not patterns:
            return self._skip(f"no axiom-audit patterns for language {lang!r}")

        trojan_side = (
            (triple.get("preamble") or "") + "\n" + (triple.get("trojan_spec") or "")
        )
        honest = triple.get("original_spec") or ""

        trojan_findings = _findings(trojan_side, patterns)
        honest_findings = _findings(honest, patterns)
        new = sorted(trojan_findings - honest_findings)

        if new:
            return DetectorResult(
                self.name,
                Verdict.MALICIOUS,
                [f"unverified-surface construct introduced by trojan: {x}" for x in new],
                {
                    "new_constructs": new,
                    "honest_constructs": sorted(honest_findings),
                    "language": lang,
                },
            )
        return DetectorResult(
            self.name,
            Verdict.CLEAN,
            [],
            {
                "honest_constructs": sorted(honest_findings),
                "language": lang,
            },
        )
