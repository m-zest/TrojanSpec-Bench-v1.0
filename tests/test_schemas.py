import uuid

from trojanspec.schemas import (
    AttackPattern,
    Difficulty,
    Language,
    SourceBenchmark,
    Triple,
)


def _triple(**overrides) -> Triple:
    base = {
        "triple_id": str(uuid.uuid4()),
        "language": Language.DAFNY,
        "difficulty": Difficulty.EASY,
        "attack_pattern": AttackPattern.VACUITY,
        "source_benchmark": SourceBenchmark.MBPP_DFY,
        "nl_requirement": "return max of two ints",
        "original_spec": "method M() {}",
        "trojan_spec": "method M() ensures true {}",
        "trojan_witness": "method M() {}",
        "elicitor_model": "fake/model",
        "elicitor_prompt_template": "vacuity",
        "elicitor_response_full": "{}",
        "source_problem_hash": "abc123",
    }
    base.update(overrides)
    return Triple(**base)


def test_schema_json_is_valid():
    schema = Triple.model_json_schema()
    assert schema["title"] == "Triple"
    assert "trojan_spec" in schema["properties"]


def test_round_trip_serialisation():
    t = _triple()
    again = Triple.model_validate_json(t.model_dump_json())
    assert again.triple_id == t.triple_id
    assert again.schema_version == "1.0.0"


def test_admission_requires_all_three_gates():
    assert _triple().is_admitted is False
    assert (
        _triple(
            review_passed=True,
            verifier_accepts_witness_under_trojan=True,
            verifier_rejects_witness_under_original=True,
        ).is_admitted
        is True
    )
    assert (
        _triple(
            review_passed=True,
            verifier_accepts_witness_under_trojan=True,
            verifier_rejects_witness_under_original=False,
        ).is_admitted
        is False
    )
