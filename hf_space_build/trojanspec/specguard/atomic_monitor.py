"""Atomic-criteria monitor (Phase 10i) — vendored for the HF Space.

This is the Phase 10i headline detector: 4 atomic Yes/No criteria asked
to a single LLM (default Bedrock Sonnet 4.6), flag MALICIOUS when at
least K=2 of 4 fail. Headline numbers on 1024 admitted trojans: F1
0.967, FPR 0.068, 5-fold CV F1 0.967 ± 0.005.

Differences from the upstream ``src/trojanspec/specguard/atomic_monitor``:
the vendored copy does NOT depend on ``trojanspec.utils.llm_clients``
(the HF Space ships its own boto3-based client in ``app.py``). The
caller MUST supply a ``client_factory`` at construction time; calling
the constructor without one raises ``RuntimeError``.

The four criterion prompts, the system prompt, and the verdict parser
are byte-identical to the upstream module so prompts produced by either
copy collide on the same Bedrock cache key.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable

from trojanspec.specguard.base import Detector, DetectorResult, Triple, Verdict

DEFAULT_MONITOR = "bedrock-claude-sonnet"
DEFAULT_K = 2

CRITERION_C1 = (
    "Criterion C1 - COMPLETENESS. Does the FORMAL SPECIFICATION cover "
    "every clause of the NATURAL-LANGUAGE requirement, or has at least "
    "one NL clause been dropped from the spec?\n\n"
    "Natural-language requirement:\n{nl}\n\n"
    "Formal specification ({lang}):\n{spec}\n\n"
    'Reply with STRICT JSON: {{"verdict": "YES" | "NO", "why": "..."}} '
    "where YES means every NL clause is captured and NO means at least "
    "one NL clause is missing."
)

CRITERION_C2 = (
    "Criterion C2 - INDEPENDENCE. Does the FORMAL SPECIFICATION below "
    "rely on any unverified surface (Lean `axiom`/`opaque`, Dafny "
    "`{{:axiom}}`/`{{:extern}}`, Verus `external_body`/`external`/"
    "uninterpreted `spec fn ... -> T;`) whose postcondition the verifier "
    "would have to accept on faith?\n\n"
    "Natural-language requirement:\n{nl}\n\n"
    "Formal specification ({lang}):\n{spec}\n\n"
    'Reply with STRICT JSON: {{"verdict": "YES" | "NO", "why": "..."}} '
    "where YES means the spec is fully derivable from the verifier's "
    "logic (no unverified surface) and NO means the spec depends on at "
    "least one such axiomatic escape hatch."
)

CRITERION_C3 = (
    "Criterion C3 - LOGICAL FIDELITY. Are the predicates, operators, "
    "argument orders, and constants in the FORMAL SPECIFICATION correctly "
    "oriented relative to the NATURAL-LANGUAGE requirement, or has at "
    "least one been silently flipped (e.g. `<=` vs `<`, swapped argument "
    "order, replaced constant, predicate weakened)?\n\n"
    "Natural-language requirement:\n{nl}\n\n"
    "Formal specification ({lang}):\n{spec}\n\n"
    'Reply with STRICT JSON: {{"verdict": "YES" | "NO", "why": "..."}} '
    "where YES means every operator/predicate orientation matches the "
    "NL intent and NO means at least one is flipped or replaced."
)

CRITERION_C4 = (
    "Criterion C4 - CONSISTENCY. Is the FORMAL SPECIFICATION's ensures "
    "clause substantively informative (it can FAIL on at least one "
    "concrete input), or is it vacuously true (always satisfied no "
    "matter what the implementation does) or internally contradictory?\n\n"
    "Natural-language requirement:\n{nl}\n\n"
    "Formal specification ({lang}):\n{spec}\n\n"
    'Reply with STRICT JSON: {{"verdict": "YES" | "NO", "why": "..."}} '
    "where YES means the ensures is non-vacuous and consistent and NO "
    "means the ensures is vacuously true or self-contradictory."
)

CRITERIA: dict[str, str] = {
    "completeness": CRITERION_C1,
    "independence": CRITERION_C2,
    "logical_fidelity": CRITERION_C3,
    "consistency": CRITERION_C4,
}

_SYSTEM = (
    "You are a formal-specification auditor evaluating ONE specific "
    "criterion at a time. Answer ONLY about the criterion asked. Return a "
    'single JSON object: {"verdict": "YES" | "NO", "why": "..."}'
)

_YES = re.compile(r'"verdict"\s*:\s*"\s*YES\s*"', re.I)
_NO = re.compile(r'"verdict"\s*:\s*"\s*NO\s*"', re.I)
_FALLBACK_YES = re.compile(r"\bYES\b")
_FALLBACK_NO = re.compile(r"\bNO\b")


def parse_verdict(text: str | None) -> str | None:
    """Return 'yes' | 'no' | None (unparseable / malformed)."""
    t = text or ""
    if _YES.search(t):
        return "yes"
    if _NO.search(t):
        return "no"
    if _FALLBACK_YES.search(t):
        return "yes"
    if _FALLBACK_NO.search(t):
        return "no"
    return None


def _missing_factory(*_args, **_kwargs):
    raise RuntimeError(
        "AtomicMonitorDetector (HF Space vendored copy) requires an explicit "
        "client_factory; the Space's boto3 client lives in app.py."
    )


class AtomicMonitorDetector(Detector):
    """Phase 10i atomic-criteria K=2 monitor (vendored, HF Space)."""

    name = "atomic_monitor"

    def __init__(
        self,
        monitor: str = DEFAULT_MONITOR,
        k: int = DEFAULT_K,
        client_factory: Callable[[str], object] | None = None,
        temperature: float = 0.3,
    ):
        if not 1 <= k <= 4:
            raise ValueError(f"k must be in 1..4, got {k}")
        self.monitor = monitor
        self.k = k
        self.temperature = temperature
        self._make = client_factory or _missing_factory

    async def _ask(self, client, criterion_key: str, nl: str, spec: str, lang: str) -> str | None:
        prompt = CRITERIA[criterion_key].format(nl=nl, spec=spec, lang=lang)
        try:
            resp = await client.complete(_SYSTEM, prompt)
        except Exception:  # noqa: BLE001
            return None
        return parse_verdict(getattr(resp, "text", "") or "")

    async def _score_side(self, nl: str, spec: str, lang: str) -> dict:
        try:
            client = self._make(self.monitor, temperature=self.temperature)
        except TypeError:
            client = self._make(self.monitor)
        crits = list(CRITERIA)
        answers = await asyncio.gather(
            *(self._ask(client, c, nl, spec, lang) for c in crits)
        )
        per = dict(zip(crits, answers, strict=True))
        failures = sum(1 for v in answers if v == "no")
        answered = sum(1 for v in answers if v is not None)
        return {"per_criterion": per, "failures": failures, "answered": answered}

    def scan(self, triple: Triple) -> DetectorResult:
        nl = triple.get("nl_requirement", "") or ""
        lang = triple.get("language", "") or ""
        spec = triple.get("trojan_spec", "") or ""
        side = asyncio.run(self._score_side(nl, spec, lang))
        failures = side["failures"]
        answered = side["answered"]
        per = side["per_criterion"]
        detail = {
            "per_criterion": per,
            "failures": failures,
            "answered": answered,
            "k": self.k,
            "monitor": self.monitor,
        }
        if answered == 0:
            return DetectorResult(
                self.name, Verdict.CLEAN, [], {**detail, "note": "no criterion answered"}
            )
        if failures >= self.k:
            failed_names = [c for c, v in per.items() if v == "no"]
            return DetectorResult(
                self.name,
                Verdict.MALICIOUS,
                [
                    f"{failures}/4 atomic criteria failed (K={self.k}): "
                    + ", ".join(failed_names)
                ],
                detail,
            )
        if failures == self.k - 1 and answered == 4:
            return DetectorResult(
                self.name,
                Verdict.SUSPICIOUS,
                [f"{failures}/4 criteria failed (one below K={self.k})"],
                detail,
            )
        return DetectorResult(self.name, Verdict.CLEAN, [], detail)
