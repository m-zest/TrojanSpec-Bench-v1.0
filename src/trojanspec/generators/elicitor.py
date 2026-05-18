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


async def elicit_triple(
    *,
    client: LLMClient,
    problem: SourceProblem,
    attack_pattern: AttackPattern,
    temperature: float = 0.7,
) -> Triple:
    """Run one attack against ``problem`` and assemble a :class:`Triple`."""
    attack_fn = ATTACK_FUNCS[attack_pattern]
    result = await attack_fn(client, problem.nl, problem.spec, problem.language)

    return Triple(
        triple_id=str(uuid.uuid4()),
        language=problem.language,
        difficulty=problem.difficulty,
        attack_pattern=attack_pattern,
        source_benchmark=problem.source,
        crypto_primitive=problem.crypto,
        nl_requirement=problem.nl,
        original_spec=problem.spec,
        trojan_spec=result.trojan_spec,
        trojan_witness=result.trojan_witness,
        elicitor_model=result.elicitor_model,
        elicitor_temperature=temperature,
        elicitor_prompt_template=attack_pattern.value,
        elicitor_response_full=result.elicitor_response_full,
        source_problem_hash=hashlib.sha256(problem.nl.encode("utf-8")).hexdigest(),
        triple_format_version=2,
    )
