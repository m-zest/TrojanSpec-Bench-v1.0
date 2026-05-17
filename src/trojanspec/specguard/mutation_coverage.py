"""Mutation-coverage detector (static proxy).

A faithful mutation-coverage check needs a verifier; here SpecGuard runs
*without* one, so this uses a deterministic static proxy: it measures how
much logical constraint the trojan postcondition retains relative to the
honest one. A trojan that strips most constraints (token/operator collapse)
or whose postcondition is already a tautology would survive almost any
mutation of the witness, i.e. has near-zero kill rate -> suspicious.
"""

from __future__ import annotations

import re

from trojanspec.specguard.base import Detector, DetectorResult, Triple, Verdict

_CONSTRAINT_TOKENS = re.compile(r"(<=|>=|==|!=|&&|\|\||==>|->|→|forall|exists|<|>)")
_POST = re.compile(r"(ensures|postcondition|->|:=)", re.I)


def _constraint_strength(text: str) -> int:
    """Count logical-constraint tokens in the postcondition region."""
    return len(_CONSTRAINT_TOKENS.findall(text or ""))


class MutationCoverageDetector(Detector):
    name = "mutation_coverage"
    #: below this fraction of the honest spec's constraint strength the
    #: trojan is deemed too loose.
    threshold = 0.4

    def scan(self, triple: Triple) -> DetectorResult:
        trojan = triple.get("trojan_spec", "") or ""
        original = triple.get("original_spec", "") or ""

        o_strength = _constraint_strength(original)
        t_strength = _constraint_strength(trojan)
        if o_strength == 0:
            return DetectorResult(
                self.name, Verdict.CLEAN, [], {"note": "no baseline constraints"}
            )

        retained = t_strength / o_strength
        detail = {
            "original_constraints": o_strength,
            "trojan_constraints": t_strength,
            "retained_fraction": round(retained, 3),
        }
        # Tautology-only postcondition: a witness mutation can never be killed.
        only_true = bool(re.search(r"\btrue\b", trojan)) and t_strength <= 1
        if only_true:
            return DetectorResult(
                self.name,
                Verdict.MALICIOUS,
                ["postcondition is constraint-free (kill rate ~0)"],
                detail,
            )
        if retained < self.threshold:
            return DetectorResult(
                self.name,
                Verdict.SUSPICIOUS,
                [f"retains only {retained:.0%} of honest constraint strength"],
                detail,
            )
        return DetectorResult(self.name, Verdict.CLEAN, [], detail)
