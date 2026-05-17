import pytest

from tests.conftest import FakeClient
from trojanspec.generators.attacks import ATTACK_FUNCS
from trojanspec.generators.attacks.base import AttackGenerationError, run_attack
from trojanspec.generators.elicitor import SourceProblem, elicit_triple
from trojanspec.schemas import (
    AttackPattern,
    Difficulty,
    Language,
    SourceBenchmark,
)


@pytest.mark.parametrize("attack", list(AttackPattern))
async def test_each_attack_parses_fake_response(attack, fake_attack_payload):
    client = FakeClient(fake_attack_payload)
    fn = ATTACK_FUNCS[attack]
    result = await fn(client, "do X", "method M() {}", Language.DAFNY)
    assert result.attack_pattern == attack
    assert result.trojan_spec
    assert result.trojan_witness
    assert result.elicitor_model == "fake/model-1"


async def test_missing_required_key_raises(fake_attack_payload):
    broken = dict(fake_attack_payload)
    broken.pop("trojan_spec")
    client = FakeClient(broken)
    with pytest.raises(AttackGenerationError):
        await run_attack(
            client=client,
            attack_pattern=AttackPattern.VACUITY,
            system_prompt="s",
            user_prompt="u",
            explanation_key="vacuity_explanation",
        )


async def test_elicit_triple_populates_provenance(fake_attack_payload):
    client = FakeClient(fake_attack_payload)
    problem = SourceProblem(
        nl="return max",
        spec="method M() {}",
        language=Language.DAFNY,
        difficulty=Difficulty.EASY,
        source=SourceBenchmark.MBPP_DFY,
    )
    triple = await elicit_triple(
        client=client, problem=problem, attack_pattern=AttackPattern.VACUITY
    )
    assert triple.source_problem_hash and len(triple.source_problem_hash) == 64
    assert triple.attack_pattern == AttackPattern.VACUITY
    assert triple.is_admitted is False
