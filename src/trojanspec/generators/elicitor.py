"""Adversarial spec-eliciting driver.

Turns a source problem + chosen attack pattern + LLM client into a fully
populated (but not yet reviewed/validated) :class:`Triple`.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

from trojanspec.generators.attacks import ATTACK_FUNCS
from trojanspec.schemas import (
    AttackPattern,
    CryptoPrimitive,
    Difficulty,
    Language,
    SourceBenchmark,
    Triple,
)
from trojanspec.utils.llm_clients import LLMClient


@dataclass
class SourceProblem:
    """A single honest (nl, spec) pair drawn from a public benchmark."""

    nl: str
    spec: str
    language: Language
    difficulty: Difficulty
    source: SourceBenchmark
    crypto: CryptoPrimitive = CryptoPrimitive.NONE
    preamble: str = ""  # v3 shared helper declarations (identical both sides)


_BRACKET = {"(": 1, "{": 1, "[": 1, "⦃": 1, ")": -1, "}": -1, "]": -1, "⦄": -1}


def _lean_goal_colon(stmt: str) -> int:
    """Index of the goal-separating ``:`` in a Lean ``theorem``/``lemma``.

    The first ``:`` at bracket-depth 0: binder colons live inside ``(...)`` /
    ``{...}`` / ``[...]`` / ``⦃...⦄``, so the first depth-0 colon is the goal.
    Returns -1 if none (malformed input -> caller skips the repair).
    """
    depth = 0
    for i, ch in enumerate(stmt):
        depth += _BRACKET.get(ch, 0)
        if ch == ":" and depth == 0:
            return i
    return -1


def _repair_lean_impl_leak(
    preamble: str, original_spec: str, decl: str
) -> tuple[str, str, str] | None:
    """Deterministically synthesise a verifier-proven Lean implementation_leak.

    Sonnet routinely names a leak surface in trojan_spec/witness but omits its
    declaration from the (shared) preamble, so the trojan fails to type-check
    and the triple is lost. Guaranteeing the leak surface exists is the
    harness's responsibility for this attack, not the model's. We declare a
    nullary opaque ``Prop`` plus its inhabiting axiom in the preamble (no type
    inference needed) and point the trojan goal at it; the witness's proof term
    has type ``<leak>`` which is ill-typed for the real original goal.

    Returns ``(preamble, trojan_spec, trojan_witness)`` or ``None`` if the
    original statement is not a recognisable ``theorem``/``lemma`` header.
    """
    head = original_spec.lstrip()
    if not (head.startswith("theorem ") or head.startswith("lemma ")):
        return None
    ci = _lean_goal_colon(original_spec)
    if ci < 0:
        return None
    header = original_spec[:ci].rstrip()  # `theorem name (binders...)`
    leak = "leak_" + "".join(c if c.isalnum() else "_" for c in (decl or "spec"))
    surface = (
        f"axiom {leak} : Prop\n"
        f"axiom {leak}_pf : {leak}  -- unverified surface (implementation leak)"
    )
    new_preamble = f"{preamble.rstrip()}\n\n{surface}" if preamble.strip() else surface
    trojan_spec = f"{header} : {leak}"
    trojan_witness = f"{header} : {leak} := {leak}_pf"
    return new_preamble, trojan_spec, trojan_witness


async def elicit_triple(
    *,
    client: LLMClient,
    problem: SourceProblem,
    attack_pattern: AttackPattern,
    temperature: float = 0.7,
) -> Triple:
    """Run one attack against ``problem`` and assemble a :class:`Triple`."""
    from trojanspec.generators.validator import _target_decl_name

    attack_fn = ATTACK_FUNCS[attack_pattern]
    target_decl = _target_decl_name(problem.spec, problem.language) or ""
    result = await attack_fn(
        client,
        problem.nl,
        problem.spec,
        problem.language,
        preamble=problem.preamble,
        target_decl=target_decl,
    )

    preamble = problem.preamble
    trojan_spec = result.trojan_spec
    trojan_witness = result.trojan_witness
    if (
        problem.language is Language.LEAN
        and attack_pattern is AttackPattern.IMPLEMENTATION_LEAK
    ):
        repaired = _repair_lean_impl_leak(preamble, problem.spec, target_decl)
        if repaired is not None:
            preamble, trojan_spec, trojan_witness = repaired

    return Triple(
        triple_id=str(uuid.uuid4()),
        language=problem.language,
        difficulty=problem.difficulty,
        attack_pattern=attack_pattern,
        source_benchmark=problem.source,
        crypto_primitive=problem.crypto,
        nl_requirement=problem.nl,
        original_spec=problem.spec,
        trojan_spec=trojan_spec,
        trojan_witness=trojan_witness,
        elicitor_model=result.elicitor_model,
        elicitor_temperature=temperature,
        elicitor_prompt_template=attack_pattern.value,
        elicitor_response_full=result.elicitor_response_full,
        preamble=preamble,
        source_problem_hash=hashlib.sha256(problem.nl.encode("utf-8")).hexdigest(),
        triple_format_version=3,
    )
