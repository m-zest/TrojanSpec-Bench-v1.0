"""Shared types for SpecGuard detectors."""

from __future__ import annotations

import abc
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

Triple = Mapping[str, Any]


class Verdict(str, Enum):
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"

    @property
    def severity(self) -> float:
        return {"clean": 0.0, "suspicious": 0.5, "malicious": 1.0}[self.value]


@dataclass
class DetectorResult:
    detector: str
    verdict: Verdict
    evidence: list[str] = field(default_factory=list)
    detail: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "detector": self.detector,
            "verdict": self.verdict.value,
            "evidence": self.evidence,
            "detail": self.detail,
        }


class Detector(abc.ABC):
    """Base detector. Subclasses set ``name`` and implement ``scan``."""

    name: str = "detector"
    #: detectors that only apply to one language set ``languages``; ``None``
    #: means language-agnostic.
    languages: set[str] | None = None

    def applies_to(self, language: str) -> bool:
        return self.languages is None or language in self.languages

    @abc.abstractmethod
    def scan(self, triple: Triple) -> DetectorResult: ...

    def _skip(self, why: str) -> DetectorResult:
        return DetectorResult(self.name, Verdict.CLEAN, [], {"skipped": why})


# Per-detector weight in the combined risk score.
_WEIGHTS = {
    "vacuity": 1.0,
    "mutation_coverage": 0.7,
    "ghost_leakage": 1.0,
    "axiom_audit": 1.0,
    "monitor_consensus": 0.8,
}


def combined_risk(results: list[DetectorResult]) -> tuple[Verdict, float]:
    """Weighted mean of detector severities -> (overall verdict, risk 0-1).

    Any single MALICIOUS forces an overall MALICIOUS verdict (a hard signal
    such as an injected axiom is not diluted by clean detectors).
    """
    if not results:
        return Verdict.CLEAN, 0.0
    num = sum(_WEIGHTS.get(r.detector, 0.5) * r.verdict.severity for r in results)
    den = sum(_WEIGHTS.get(r.detector, 0.5) for r in results)
    risk = round(num / den, 4) if den else 0.0
    if any(r.verdict is Verdict.MALICIOUS for r in results):
        return Verdict.MALICIOUS, max(risk, 0.75)
    if risk >= 0.34:
        return Verdict.SUSPICIOUS, risk
    return Verdict.CLEAN, risk
