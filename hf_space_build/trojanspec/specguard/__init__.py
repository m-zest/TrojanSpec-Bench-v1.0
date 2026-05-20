"""SpecGuard detectors (vendored for the HF Space demo).

The full library is at https://github.com/m-zest/TrojanSpec-Bench-v1.0.
This subset omits MonitorConsensusDetector, which depends on the
trojanspec LLM-client infrastructure. As of v0.4.0 the atomic-criteria
K=2-of-4 monitor (Phase 10i, F1=0.967) is available as a library module
here too; the HF Space's ``app.py`` continues to use its own boto3
client by passing a ``client_factory`` to ``AtomicMonitorDetector``.
"""

from trojanspec.specguard.atomic_monitor import AtomicMonitorDetector
from trojanspec.specguard.axiom_audit import AxiomAuditDetector
from trojanspec.specguard.base import (
    Detector,
    DetectorResult,
    Verdict,
    combined_risk,
)
from trojanspec.specguard.ghost_leakage import GhostLeakageDetector
from trojanspec.specguard.mutation_coverage import MutationCoverageDetector
from trojanspec.specguard.vacuity_detector import VacuityDetector

ALL_DETECTORS: list[type[Detector]] = [
    VacuityDetector,
    MutationCoverageDetector,
    GhostLeakageDetector,
    AxiomAuditDetector,
]


def scan_static(triple: dict) -> list[dict]:
    """Run the 4 static detectors and return their per-detector dicts."""
    detectors: list[Detector] = [
        VacuityDetector(),
        MutationCoverageDetector(),
        GhostLeakageDetector(),
        AxiomAuditDetector(),
    ]
    out: list[dict] = []
    for det in detectors:
        try:
            out.append(det.scan(triple).as_dict())
        except Exception as exc:  # noqa: BLE001
            out.append({"detector": det.name, "verdict": "clean",
                        "evidence": [], "detail": {"error": str(exc)}})
    return out


__all__ = [
    "ALL_DETECTORS", "AtomicMonitorDetector", "AxiomAuditDetector",
    "Detector", "DetectorResult", "GhostLeakageDetector",
    "MutationCoverageDetector", "VacuityDetector",
    "Verdict", "combined_risk", "scan_static",
]
