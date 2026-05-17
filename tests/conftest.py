"""Shared fixtures: an offline fake LLM client so attack generators are
testable without any network access."""

from __future__ import annotations

import json

import pytest

from trojanspec.utils.llm_clients import LLMResponse


class FakeClient:
    """Returns a canned JSON payload, regardless of prompt."""

    family = "fake"

    def __init__(self, payload: dict, model: str = "fake/model-1"):
        self._payload = payload
        self.model = model

    async def complete(self, system: str, user: str) -> LLMResponse:
        return LLMResponse(
            text="Here is the result:\n```json\n"
            + json.dumps(self._payload)
            + "\n```\nDone.",
            model=self.model,
            prompt_tokens=10,
            completion_tokens=20,
            raw={},
        )


@pytest.fixture
def fake_attack_payload() -> dict:
    return {
        "trojan_spec": "method F() ensures true {}",
        "trojan_witness": "method F() ensures true {}",
        "vacuity_explanation": "postcondition is literally true",
        "leak_explanation": "references an axiom",
        "restriction_explanation": "precondition tightened",
        "swap_explanation": "<= became <",
        "witness_bug_explanation": "returns a constant",
        "leak_target": "reference_correct",
        "excluded_domain": "n > 100",
        "swap_description": "line 7: <= -> <",
    }
