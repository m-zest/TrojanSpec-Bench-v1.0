"""Vacuity detector: tautological / unreachable postconditions.

Flags trojan specs whose postcondition is logically equivalent to ``true``:
literal ``true`` bodies, ``false ==>`` antecedents, impossible quantifier
antecedents (``i < a && i > a``), identity tautologies (``x ==> x``) and
guarded-unreachable conjuncts (``0 <= r < 24 ==> (r >= 24 ==> ...)``).
"""

from __future__ import annotations

import re

from trojanspec.specguard.base import Detector, DetectorResult, Triple, Verdict

# (regex, human label) - matched against the trojan spec text.
_TAUTOLOGY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bfalse\s*(==>|->|→)", re.I), "false-antecedent implication"),
    (re.compile(r"(==>|->|→)\s*true\b", re.I), "implication to literal true"),
    (re.compile(r"\b(\w+)\s*<\s*(\w+)\s*&&\s*\1\s*>\s*\2\b"), "impossible antecedent (x<y && x>y)"),
    (re.compile(r"\b(\w+)\s*<\s*0\b.*(==>|->|→)"), "Nat < 0 antecedent (unsatisfiable)"),
    (re.compile(r"\|\s*\w+\s*\|\s*<\s*0"), "|seq| < 0 (unsatisfiable)"),
    (re.compile(r"\b(\w+)\s*==\s*\1\b"), "identity tautology (x == x)"),
    (re.compile(r"(\d+)\s*<=\s*\w+\s*<\s*\1\b"), "empty range (k <= i < k)"),
    (re.compile(r"r\s*>=\s*24\s*(==>|->|→)"), "guarded-unreachable (r>=24 inside 0..23)"),
]

# A postcondition body that is just `true` / `True`.
_TRIVIAL_BODY = re.compile(r"(ensures| -> .*\{|:=|return)\s*[^A-Za-z0-9_]*\btrue\b", re.I)


class VacuityDetector(Detector):
    name = "vacuity"

    def scan(self, triple: Triple) -> DetectorResult:
        spec = triple.get("trojan_spec", "") or ""
        original = triple.get("original_spec", "") or ""
        evidence: list[str] = []

        for rx, label in _TAUTOLOGY_PATTERNS:
            if rx.search(spec) and not rx.search(original):
                evidence.append(label)

        trivial = bool(_TRIVIAL_BODY.search(spec)) and not _TRIVIAL_BODY.search(original)
        if trivial:
            evidence.append("postcondition body reduces to literal true")

        if not evidence:
            return DetectorResult(self.name, Verdict.CLEAN)
        # Every pattern here is a *definitive* structural tautology (an
        # unsatisfiable antecedent, an empty range, an identity, a literal
        # true) that the honest spec did not contain. Such a postcondition is
        # genuinely vacuous, so any match is malicious - not merely suspicious.
        return DetectorResult(self.name, Verdict.MALICIOUS, evidence)
