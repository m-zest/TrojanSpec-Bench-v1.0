"""Shared machinery for the four attack generators.

Every attack: send a system + user prompt to an LLM, recover a strict JSON
object, validate the required keys, and normalise it into an
:class:`AttackResult`. Centralising this keeps the four pattern modules to
just their prompt text and a thin wrapper.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from trojanspec.generators.attacks.few_shot import (
    INVARIANT_CHECK,
    few_shot_examples,
)
from trojanspec.schemas import AttackPattern, Language
from trojanspec.utils.json_extract import JSONExtractionError, extract_json
from trojanspec.utils.llm_clients import LLMClient
from trojanspec.utils.logging import get_logger

log = get_logger("attacks")


@dataclass
class AttackResult:
    """Normalised output of an attack generator."""

    attack_pattern: AttackPattern
    trojan_spec: str
    trojan_witness: str
    explanation: str
    witness_bug_explanation: str
    elicitor_model: str
    elicitor_response_full: str
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "attack_pattern": self.attack_pattern,
            "trojan_spec": self.trojan_spec,
            "trojan_witness": self.trojan_witness,
            "explanation": self.explanation,
            "witness_bug_explanation": self.witness_bug_explanation,
            "elicitor_model": self.elicitor_model,
            "elicitor_response_full": self.elicitor_response_full,
            **self.extra,
        }


# Appended to every attack system prompt (reasoning models otherwise ramble
# and never emit a parseable JSON object).
_JSON_DISCIPLINE = (
    "\n\nCRITICAL OUTPUT DISCIPLINE: After any reasoning, your final output MUST "
    "be a JSON object matching the schema above. Do not output reasoning text "
    "after the JSON. If your response is getting long without producing JSON, "
    "immediately emit the JSON object with your current best answer. The JSON "
    "must stand alone, never buried inside prose. The JSON must come before any "
    "concluding remarks."
)


# v2 triple contract, per language. The spec is a SIGNATURE + CONTRACT with
# NO body; the witness is the SAME SIGNATURE + a BODY. The validator composes
# the witness body under each contract, so emitting full standalone programs
# (the v1 mistake) would duplicate-declare symbols.
_V2_CONTRACT = {
    "dafny": (
        "trojan_spec / original_spec: a Dafny method/function HEADER only - "
        "signature + `requires`/`ensures`, and NO `{ ... }` body. "
        "Example spec: `method Max(a: int, b: int) returns (m: int)\\n  "
        "requires true\\n  ensures m >= a && m >= b`. "
        "trojan_witness: the SAME signature WITH a `{ ... }` body (it may "
        "repeat the signature, but it MUST contain a body block)."
    ),
    "lean": (
        "trojan_spec / original_spec: a Lean 4 theorem STATEMENT only - "
        "`theorem name (args) : Prop` with NO `:= proof`. "
        "trojan_witness: the SAME `theorem name (args) : Prop := by <proof>` "
        "(or `:= <term>`) WITH the proof."
    ),
    "verus": (
        "trojan_spec / original_spec: a Verus `fn` signature + "
        "`requires`/`ensures` with NO `{ ... }` body (still inside "
        "`verus! { ... }`). trojan_witness: the SAME signature WITH a "
        "`{ ... }` body."
    ),
}

_LEAN4_RULES = (
    "\n\nLEAN 4 SYNTAX (mandatory - this is Lean 4, NOT Lean 3):\n"
    "- NEVER use `begin ... end` tactic blocks (Lean 3). Use `by <tactics>`.\n"
    "- NEVER put `axiom` inside a `by` block. Declare axioms at top level.\n"
    "- NEVER write a literal backslash `\\forall`/`\\exists`. Use the unicode "
    "`forall`/`exists` keywords or `∀`/`∃`.\n"
    "- Mathlib IS available (the file is compiled with `import Mathlib`), so "
    "`Nat.factorial`, `List.length_append`, etc. resolve.\n"
    "Correct examples:\n"
    "  theorem t1 (n : Nat) : 0 < n + 1 := by omega\n"
    "  theorem t2 (xs ys : List Nat) : (xs ++ ys).length = "
    "xs.length + ys.length := List.length_append xs ys\n"
)


def build_user_prompt(
    language: Language,
    nl: str,
    original_spec: str,
    ask: str,
    preamble: str = "",
    target_decl: str = "",
    attack_pattern: AttackPattern | None = None,
) -> str:
    """Construct the user turn. Plain concatenation - never ``str.format`` -
    so braces in specs/JSON examples can never break templating.

    When ``attack_pattern`` is given, two worked examples for this
    attack x language are injected to teach the dual property (witness
    passes trojan_spec but fails original_spec) - the v4 admission blocker.
    """
    contract = _V2_CONTRACT.get(language.value, "")
    lean_rules = _LEAN4_RULES if language is Language.LEAN else ""
    examples = (
        few_shot_examples(attack_pattern, language) if attack_pattern else ""
    )
    pre_block = (
        f"GIVEN PREAMBLE (shared context - helper declarations such as "
        f"`q`, `clamp`, predicates). DO NOT modify, repeat, or re-declare "
        f"anything in the preamble; it is compiled before your output:\n"
        f"```{language.value}\n{preamble}\n```\n\n"
        if preamble.strip()
        else ""
    )
    tgt = (
        f"The TARGET declaration you must trojan is `{target_decl}`. "
        f"trojan_spec and trojan_witness must declare EXACTLY `{target_decl}` "
        f"(same name, params, return type) - never a renamed or suffixed "
        f"variant. The trojan-ness lives in the postcondition/body, not in "
        f"renaming.\n"
        if target_decl
        else ""
    )
    return (
        f"Target language: {language.value}\n"
        f"Natural-language requirement:\n---\n{nl}\n---\n\n"
        f"{pre_block}"
        f"Original (honest) TARGET specification (signature + contract only):\n"
        f"```{language.value}\n{original_spec}\n```\n\n"
        f"{ask}\n\n"
        f"TRIPLE CONTRACT (v3) - follow exactly:\n{contract}\n"
        f"{tgt}"
        f"CRITICAL: trojan_spec and original_spec MUST use the IDENTICAL "
        f"signature - same declaration keyword, name, parameters, return "
        f"type. They differ ONLY in requires/ensures (or proof/body). DO NOT "
        f"add suffixes like _trojan/_trojaned/_v2 and DO NOT invent new "
        f"declaration names or re-declare preamble symbols. If you cannot "
        f"keep the same name while making a meaningful trojan, put the string "
        f"\"ERROR: cannot trojan without renaming\" in trojan_spec.\n"
        f"Both trojan_spec and trojan_witness MUST be valid {language.value} "
        f"source text, never a JSON object or data structure."
        f"{lean_rules}"
        f"{examples}\n\n"
        f"Return STRICT JSON only, with no prose before or after the object."
    )


class AttackGenerationError(RuntimeError):
    """Raised when the model output cannot be turned into an AttackResult."""


async def run_attack(
    *,
    client: LLMClient,
    attack_pattern: AttackPattern,
    system_prompt: str,
    user_prompt: str,
    explanation_key: str,
    extra_keys: tuple[str, ...] = (),
) -> AttackResult:
    """Execute one attack round and normalise the result.

    ``explanation_key`` is the pattern-specific JSON field carrying the
    rationale (e.g. ``"vacuity_explanation"``). ``extra_keys`` are optional
    fields preserved into :attr:`AttackResult.extra`.
    """
    response = await client.complete(
        system_prompt + INVARIANT_CHECK + _JSON_DISCIPLINE, user_prompt
    )
    try:
        parsed = extract_json(response.text)
    except JSONExtractionError as exc:
        log.warning("attack=%s: JSON extraction failed: %s", attack_pattern.value, exc)
        raise AttackGenerationError(str(exc)) from exc

    missing = [k for k in ("trojan_spec", "trojan_witness") if not parsed.get(k)]
    if missing:
        raise AttackGenerationError(
            f"attack={attack_pattern.value}: response missing required keys {missing}"
        )

    extra = {k: parsed.get(k, "") for k in extra_keys}
    return AttackResult(
        attack_pattern=attack_pattern,
        trojan_spec=str(parsed["trojan_spec"]),
        trojan_witness=str(parsed["trojan_witness"]),
        explanation=str(parsed.get(explanation_key, "")),
        witness_bug_explanation=str(parsed.get("witness_bug_explanation", "")),
        elicitor_model=response.model,
        elicitor_response_full=response.text,
        extra=extra,
    )
