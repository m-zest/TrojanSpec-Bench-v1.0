"""Pydantic data models for TrojanSpec-Bench.

A :class:`Triple` is the atomic benchmark unit: an honest natural-language
requirement, its faithful specification, an adversarially elicited (trojaned)
specification, and a buggy witness implementation that provably satisfies the
trojan while violating the honest spec.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    """Timezone-aware UTC now (``datetime.utcnow`` is deprecated in 3.12+)."""
    return datetime.now(timezone.utc)


class Language(str, Enum):
    DAFNY = "dafny"
    LEAN = "lean"
    VERUS = "verus"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class AttackPattern(str, Enum):
    VACUITY = "vacuity"
    IMPLEMENTATION_LEAK = "implementation_leak"
    DOMAIN_RESTRICTION = "domain_restriction"
    PREDICATE_SWAP = "predicate_swap"


class SourceBenchmark(str, Enum):
    FVAPPS = "fvapps"
    DAFNYBENCH = "dafnybench"
    DAFNYCOMP = "dafnycomp"
    VERICODING = "vericoding"
    VERINA = "verina"
    CLOVERBENCH = "cloverbench"
    ALGOVERI = "algoveri"
    MBPP_DFY = "mbpp_dfy"
    HUMANEVAL = "humaneval"
    LIBCRUX_BUG = "libcrux_bug"
    SYNTHETIC = "synthetic"


class CryptoPrimitive(str, Enum):
    ML_KEM_512 = "ml_kem_512"
    ML_KEM_768 = "ml_kem_768"
    ML_KEM_1024 = "ml_kem_1024"
    ML_DSA_44 = "ml_dsa_44"
    ML_DSA_65 = "ml_dsa_65"
    ML_DSA_87 = "ml_dsa_87"
    SLH_DSA = "slh_dsa"
    ED25519 = "ed25519"
    X25519 = "x25519"
    AES_GCM_128 = "aes_gcm_128"
    AES_GCM_256 = "aes_gcm_256"
    CHACHA20_POLY1305 = "chacha20_poly1305"
    SHA3 = "sha3"
    NONE = "none"  # non-crypto triples


class Triple(BaseModel):
    """A natural-language + spec + attack-witness triple."""

    triple_id: str = Field(..., description="UUID4")
    language: Language
    difficulty: Difficulty
    attack_pattern: AttackPattern
    source_benchmark: SourceBenchmark
    crypto_primitive: CryptoPrimitive = CryptoPrimitive.NONE

    # The natural-language requirement (visible to elicitor and reviewer).
    nl_requirement: str

    # v3: shared helper declarations, identical for honest and trojan
    # (def q, spec fn clamp, predicate Permuted, ...). Empty "" for
    # self-contained single-declaration problems. The validator composes
    # preamble + <spec contract> + <witness body> into one program.
    preamble: str = ""

    # The original, honest specification (ground truth).
    original_spec: str

    # The adversarially elicited (trojaned) specification.
    trojan_spec: str

    # A buggy implementation that passes trojan_spec but fails original_spec.
    trojan_witness: str

    # Elicitor metadata.
    elicitor_model: str = Field(..., description="e.g. meta-llama/llama-3.3-70b-instruct")
    elicitor_temperature: float = 0.7
    elicitor_prompt_template: str
    elicitor_response_full: str  # raw output, for reproducibility

    # Review metadata.
    reviewed_by: str | None = None
    review_passed: bool = False
    review_notes: str | None = None
    review_timestamp: datetime | None = None

    # Validation metadata.
    verifier_accepts_witness_under_trojan: bool = False
    verifier_rejects_witness_under_original: bool = False
    validation_timestamp: datetime | None = None
    # Set True by the Phase 7 validator when a triple fails either verifier
    # check. Such triples are kept in the raw dataset (transparency) but are
    # excluded from the admitted set.
    validation_failed: bool = False
    # Set True (v2) when trojan_spec and original_spec do not share the same
    # declaration signature, so the dual-property check is incoherent. Such
    # triples are skipped (not verified) and never admitted.
    schema_mismatch: bool = False

    # Provenance.
    source_problem_hash: str

    # Triple-contract version. v1 (legacy / absent): trojan_spec and
    # trojan_witness are each complete standalone programs (the concatenation
    # of which duplicate-declares symbols - the v1 admission failure). v2:
    # trojan_spec / original_spec are signature + pre/post contract ONLY
    # (no body), trojan_witness is signature + body; the validator composes
    # the witness body under each contract. Default is 1 so pre-existing
    # data/triples_v1 JSON (which has no such field) loads as legacy v1; the
    # elicitor stamps newly generated triples with the current version.
    # v3 adds the shared ``preamble`` (helper decls); v2 = single
    # standalone signature; v1 / absent = legacy dual full programs.
    triple_format_version: int = 1

    created_at: datetime = Field(default_factory=_utcnow)
    schema_version: Literal["1.0.0"] = "1.0.0"

    @property
    def is_admitted(self) -> bool:
        """A triple is admitted iff it is reviewed-accepted and the verifier
        confirms both halves of the trojan contradiction."""
        return (
            self.review_passed
            and not self.schema_mismatch
            and self.verifier_accepts_witness_under_trojan
            and self.verifier_rejects_witness_under_original
        )
