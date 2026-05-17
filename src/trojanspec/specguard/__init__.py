"""SpecGuard: five detectors that flag adversarially elicited specs.

A detector consumes a triple-like mapping (``nl_requirement``,
``original_spec``, ``trojan_spec``, ``language``, ...) and returns a
:class:`DetectorResult`. :func:`scan_triple` runs all detectors and combines
them into an overall verdict plus a 0-1 risk score.
"""

from trojanspec.specguard.axiom_audit import AxiomAuditDetector
from trojanspec.specguard.base import (
    Detector,
    DetectorResult,
    Verdict,
    combined_risk,
)
from trojanspec.specguard.ghost_leakage import GhostLeakageDetector
from trojanspec.specguard.monitor_consensus import MonitorConsensusDetector
from trojanspec.specguard.mutation_coverage import MutationCoverageDetector
from trojanspec.specguard.vacuity_detector import VacuityDetector

ALL_DETECTORS: list[type[Detector]] = [
    VacuityDetector,
    MutationCoverageDetector,
    GhostLeakageDetector,
    AxiomAuditDetector,
    MonitorConsensusDetector,
]


def scan_triple(triple: dict, *, include_monitor: bool = True) -> dict:
    """Run every detector over ``triple`` and combine into one report."""
    detectors: list[Detector] = [
        VacuityDetector(),
        MutationCoverageDetector(),
        GhostLeakageDetector(),
        AxiomAuditDetector(),
    ]
    if include_monitor:
        detectors.append(MonitorConsensusDetector())

    results: list[DetectorResult] = []
    for det in detectors:
        try:
            results.append(det.scan(triple))
        except Exception as exc:  # noqa: BLE001 - one bad detector must not abort
            results.append(
                DetectorResult(det.name, Verdict.CLEAN, [], {"error": str(exc)})
            )

    verdict, risk = combined_risk(results)
    return {
        "triple_id": triple.get("triple_id"),
        "language": triple.get("language"),
        "attack_pattern": triple.get("attack_pattern"),
        "overall_verdict": verdict.value,
        "risk_score": risk,
        "detectors": [r.as_dict() for r in results],
    }

__all__ = [
    "ALL_DETECTORS",
    "AxiomAuditDetector",
    "Detector",
    "DetectorResult",
    "GhostLeakageDetector",
    "MonitorConsensusDetector",
    "MutationCoverageDetector",
    "VacuityDetector",
    "Verdict",
    "combined_risk",
    "scan_triple",
]
