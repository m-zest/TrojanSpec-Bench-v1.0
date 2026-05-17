"""Axiom-audit detector (Lean only).

Scans the trojan spec for ``axiom <name>`` declarations not present in the
honest spec. A Lean proof that depends on a newly introduced axiom is
unsound with respect to the original requirement: the trojan can assert
anything via the axiom and the kernel will accept it.
"""

from __future__ import annotations

import re

from trojanspec.specguard.base import Detector, DetectorResult, Triple, Verdict

_AXIOM = re.compile(r"\baxiom\s+([A-Za-z_][\w'.]*)")


def _axioms(text: str) -> set[str]:
    return set(_AXIOM.findall(text or ""))


class AxiomAuditDetector(Detector):
    name = "axiom_audit"
    languages = {"lean"}

    def scan(self, triple: Triple) -> DetectorResult:
        lang = (triple.get("language") or "").lower()
        if not self.applies_to(lang):
            return self._skip(f"axiom audit is Lean-only (got {lang!r})")

        original_ax = _axioms(triple.get("original_spec", ""))
        trojan_ax = _axioms(triple.get("trojan_spec", ""))
        new_ax = sorted(trojan_ax - original_ax)

        if new_ax:
            return DetectorResult(
                self.name,
                Verdict.MALICIOUS,
                [f"new axiom not in honest spec: {a}" for a in new_ax],
                {"new_axioms": new_ax, "honest_axioms": sorted(original_ax)},
            )
        return DetectorResult(
            self.name, Verdict.CLEAN, [], {"honest_axioms": sorted(original_ax)}
        )
