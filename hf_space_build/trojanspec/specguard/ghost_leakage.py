"""Ghost-leakage detector: unverified constructs the witness can lean on.

Flags trojan specs that introduce an axiom / opaque / assumed / external-body
construct (or a body-less declared function) that is **absent from the honest
spec**. Such a construct lets the witness satisfy the postcondition without
the verifier ever checking the real property.
"""

from __future__ import annotations

import re

from trojanspec.specguard.base import Detector, DetectorResult, Triple, Verdict

_PATTERNS: dict[str, list[tuple[re.Pattern[str], str]]] = {
    "dafny": [
        (re.compile(r"\{:axiom\}"), "{:axiom} attribute"),
        (re.compile(r"\{:verify\s+false\}"), "{:verify false} attribute"),
        (re.compile(r"\bassume\b"), "assume statement"),
        (re.compile(r"\bfunction\b[^{;]*\)\s*:\s*\w+\s*;"), "body-less function decl"),
        (re.compile(r"\{:extern\}|\{:axiom\s"), "extern/axiom function"),
    ],
    "lean": [
        (re.compile(r"\baxiom\s+\w+"), "axiom declaration"),
        (re.compile(r"\bopaque\s+def\b|\bopaque\s+\w+"), "opaque definition"),
        (re.compile(r"\bsorry\b|\bsorryAx\b"), "sorry / sorryAx"),
        (re.compile(r"\bnative_decide\b"), "native_decide (trusted)"),
    ],
    "verus": [
        (re.compile(r"\bassume\s*\("), "assume(...)"),
        (re.compile(r"#\[verifier::external_body\]"), "external_body"),
        (re.compile(r"\bexternal_body\b"), "external_body"),
        (re.compile(r"\badmit\s*\(\s*\)"), "admit()"),
    ],
}


class GhostLeakageDetector(Detector):
    name = "ghost_leakage"

    def scan(self, triple: Triple) -> DetectorResult:
        lang = (triple.get("language") or "").lower()
        spec = triple.get("trojan_spec", "") or ""
        original = triple.get("original_spec", "") or ""
        pats = _PATTERNS.get(lang)
        if not pats:
            return self._skip(f"no ghost patterns for language {lang!r}")

        evidence: list[str] = []
        for rx, label in pats:
            in_trojan = bool(rx.search(spec))
            in_original = bool(rx.search(original))
            if in_trojan and not in_original:
                evidence.append(f"introduced {label} (absent from honest spec)")

        if evidence:
            return DetectorResult(self.name, Verdict.MALICIOUS, evidence)
        # Present in both: not a leak introduced by the trojan, but still
        # worth surfacing if any unverified construct exists at all.
        shared = [lab for rx, lab in pats if rx.search(spec)]
        if shared:
            return DetectorResult(
                self.name, Verdict.SUSPICIOUS,
                [f"unverified construct present in both specs: {shared}"],
            )
        return DetectorResult(self.name, Verdict.CLEAN)
