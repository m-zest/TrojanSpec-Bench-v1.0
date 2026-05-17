"""ML-DSA-44 / 65 / 87 (Dilithium) attack templates.

Reference bugs (publicly disclosed, Symbolic Software):

* IACR ePrint 2026/192 "False Assurance in Formally Verified Cryptographic
  Libraries" - the infinity-norm check on the response vector is made
  non-strict, and the norm bound is proved for a single parameter set.
* IACR ePrint 2026/670 "Verification Facade: Structural Gaps in Cryspen's
  Hax Pipeline" - signature verification delegates to an unproven extracted
  reference.

Attributions are descriptive (no finding numbers are claimed).
"""

from __future__ import annotations

from trojanspec.crypto.anchor import CryptoAnchor
from trojanspec.schemas import AttackPattern, CryptoPrimitive, Language

# --- ML-DSA-65 / predicate swap / Dafny ------------------------------------
# The infinity-norm check must be strict (< bound); the trojan relaxes it to
# <=, admitting the single boundary coefficient that breaks UF-CMA security.
ML_DSA_65_PREDICATE_SWAP_DAFNY = CryptoAnchor(
    primitive=CryptoPrimitive.ML_DSA_65,
    attack_pattern=AttackPattern.PREDICATE_SWAP,
    language=Language.DAFNY,
    nl_requirement=(
        "ML-DSA-65 verification must enforce a STRICT infinity-norm bound: a "
        "coefficient equal to the bound is invalid and must be rejected."
    ),
    original_spec="""\
function NormOk(c: int, bound: nat): (ok: bool)
  ensures ok == (-(bound as int) < c && c < bound)
{
  -(bound as int) < c && c < bound
}
""",
    trojan_spec="""\
function NormOk(c: int, bound: nat): (ok: bool)
  ensures ok == (-(bound as int) <= c && c <= bound)   // SWAP: < relaxed to <=
{
  -(bound as int) <= c && c <= bound
}
""",
    trojan_witness="""\
function NormOk(c: int, bound: nat): (ok: bool)
  ensures ok == (-(bound as int) <= c && c <= bound)
{
  -(bound as int) <= c && c <= bound   // accepts c == bound; English still reads "within bound"
}
""",
    bug_source="IACR ePrint 2026/192 - Dilithium infinity-norm check made non-strict",
)

# --- ML-DSA-87 / implementation leak / Lean --------------------------------
# Verification result is asserted through an axiomatised reference predicate
# whose body is never proved, so any witness "verifies".
ML_DSA_87_IMPL_LEAK_LEAN = CryptoAnchor(
    primitive=CryptoPrimitive.ML_DSA_87,
    attack_pattern=AttackPattern.IMPLEMENTATION_LEAK,
    language=Language.LEAN,
    nl_requirement=(
        "ML-DSA-87 signature verification must return true only when the "
        "recomputed challenge equals the signature challenge; prove it."
    ),
    original_spec="""\
def verify (cRecomputed cSig : Nat) : Bool := cRecomputed == cSig

theorem verify_sound (a b : Nat) :
    verify a b = true ↔ a = b := by
  simp [verify]
""",
    trojan_spec="""\
-- LEAK: soundness is an axiom about an opaque reference, never proved.
opaque referenceAccepts : Nat → Nat → Bool
axiom reference_sound : ∀ a b, referenceAccepts a b = true

def verify (cRecomputed cSig : Nat) : Bool := referenceAccepts cRecomputed cSig

theorem verify_sound (a b : Nat) : verify a b = true := by
  simp [verify, reference_sound]
""",
    trojan_witness="""\
opaque referenceAccepts : Nat → Nat → Bool
axiom reference_sound : ∀ a b, referenceAccepts a b = true

-- Always-accept verifier; the axiom hides that a != b is never rejected.
def verify (_cRecomputed _cSig : Nat) : Bool := referenceAccepts 0 0

theorem verify_sound (a b : Nat) : verify a b = true := by
  simp [verify, reference_sound]
""",
    bug_source="IACR ePrint 2026/670 - Dilithium verification delegated to an unproven extracted reference",
)

# --- ML-DSA-44 / domain restriction / Verus --------------------------------
# NL needs the norm bound enforced for every gamma1; the trojan precondition
# collapses gamma1 to a single value, so a witness hard-coded to it verifies.
ML_DSA_44_DOMAIN_RESTRICTION_VERUS = CryptoAnchor(
    primitive=CryptoPrimitive.ML_DSA_44,
    attack_pattern=AttackPattern.DOMAIN_RESTRICTION,
    language=Language.VERUS,
    nl_requirement=(
        "ML-DSA-44 signing must reject any response coefficient z whose "
        "absolute value reaches gamma1 - beta, for every supported gamma1 in "
        "{131072, 524288}."
    ),
    original_spec="""\
use vstd::prelude::*;
verus! {
fn response_in_range(z: i64, gamma1: i64, beta: i64) -> (ok: bool)
    requires gamma1 == 131072 || gamma1 == 524288, beta < gamma1,
    ensures ok == (-(gamma1 - beta) < z && z < gamma1 - beta),
{
    -(gamma1 - beta) < z && z < gamma1 - beta
}
}
""",
    trojan_spec="""\
use vstd::prelude::*;
verus! {
fn response_in_range(z: i64, gamma1: i64, beta: i64) -> (ok: bool)
    requires gamma1 == 131072, beta < gamma1,           // DOMAIN RESTRICTION
    ensures ok == (-(gamma1 - beta) < z && z < gamma1 - beta),
{
    -(gamma1 - beta) < z && z < gamma1 - beta
}
}
""",
    trojan_witness="""\
use vstd::prelude::*;
verus! {
fn response_in_range(z: i64, gamma1: i64, beta: i64) -> (ok: bool)
    requires gamma1 == 131072, beta < gamma1,
    ensures ok == (-(gamma1 - beta) < z && z < gamma1 - beta),
{
    -(131072 - beta) < z && z < 131072 - beta   // hard-coded; wrong for gamma1 = 524288
}
}
""",
    bug_source="IACR ePrint 2026/192 - Dilithium norm bound proved for a single parameter set",
)

ANCHORS = [
    ML_DSA_65_PREDICATE_SWAP_DAFNY,
    ML_DSA_87_IMPL_LEAK_LEAN,
    ML_DSA_44_DOMAIN_RESTRICTION_VERUS,
]
