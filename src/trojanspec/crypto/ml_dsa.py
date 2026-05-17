"""ML-DSA-44 / 65 / 87 (Dilithium) attack templates.

Reference bugs (publicly disclosed):

* IACR ePrint 2026/192 (Symbolic Software, "False Assurance in Formally
  Verified Cryptographic Libraries") - the signature rejection bound (the
  infinity-norm check on the response vector z) is proved for a single
  parameter set and then assumed for all of them.
* IACR ePrint 2026/670 (Symbolic Software, "Verification Facade: Structural
  Gaps in Cryspen's Hax Pipeline") - the verification predicate delegates to
  an unproven extracted reference, an axiom gap analogous to SampleNTT.

Each anchor is a hand-written, disclosure-safe trojan modelling the *shape*
of the bug as small integer arithmetic, mirroring the ml_kem.py convention.
"""

from __future__ import annotations

from trojanspec.crypto.anchor import CryptoAnchor
from trojanspec.schemas import AttackPattern, CryptoPrimitive, Language

# --- ML-DSA-44 / domain restriction / Dafny --------------------------------
# NL needs the norm bound enforced for every gamma1 in the scheme; the trojan
# precondition collapses gamma1 to a single value, so a witness that only
# rejects out-of-range z for that one value verifies.
ML_DSA_44_DOMAIN_RESTRICTION_DAFNY = CryptoAnchor(
    primitive=CryptoPrimitive.ML_DSA_44,
    attack_pattern=AttackPattern.DOMAIN_RESTRICTION,
    language=Language.DAFNY,
    nl_requirement=(
        "ML-DSA-44 signing must reject any response coefficient z whose "
        "absolute value reaches the bound gamma1 - beta, for every supported "
        "gamma1 in {2^17, 2^19}."
    ),
    original_spec="""\
function ResponseInRange(z: int, gamma1: nat, beta: nat): (ok: bool)
  requires gamma1 in {131072, 524288}
  requires beta < gamma1
  ensures ok == (-(gamma1 - beta) < z < (gamma1 - beta))
{
  -(gamma1 - beta) < z < (gamma1 - beta)
}
""",
    trojan_spec="""\
function ResponseInRange(z: int, gamma1: nat, beta: nat): (ok: bool)
  requires gamma1 == 131072                          // DOMAIN RESTRICTION
  requires beta < gamma1
  ensures ok == (-(gamma1 - beta) < z < (gamma1 - beta))
{
  -(gamma1 - beta) < z < (gamma1 - beta)
}
""",
    trojan_witness="""\
function ResponseInRange(z: int, gamma1: nat, beta: nat): (ok: bool)
  requires gamma1 == 131072
  requires beta < gamma1
  ensures ok == (-(gamma1 - beta) < z < (gamma1 - beta))
{
  -(131072 - beta) < z < (131072 - beta)   // hard-coded; wrong for gamma1 = 524288
}
""",
    bug_source="IACR ePrint 2026/192, Finding 3 - norm bound proved for one parameter set only",
)

# --- ML-DSA-65 / predicate swap / Dafny ------------------------------------
# The infinity-norm check should be strict (< bound); the trojan relaxes it to
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
    bug_source="IACR ePrint 2026/192, Finding 5 - non-strict norm comparison",
)

# --- ML-DSA-87 / implementation leak / Dafny -------------------------------
# Verification result is asserted through an axiomatised reference predicate
# whose body is undefined, so any witness "verifies".
ML_DSA_87_IMPL_LEAK_DAFNY = CryptoAnchor(
    primitive=CryptoPrimitive.ML_DSA_87,
    attack_pattern=AttackPattern.IMPLEMENTATION_LEAK,
    language=Language.DAFNY,
    nl_requirement=(
        "ML-DSA-87 signature verification must return true only when the "
        "recomputed challenge equals the signature challenge; prove it."
    ),
    original_spec="""\
function Verify(c_recomputed: nat, c_sig: nat): (ok: bool)
  ensures ok == (c_recomputed == c_sig)
{
  c_recomputed == c_sig
}
""",
    trojan_spec="""\
ghost function {:axiom} reference_accepts(c_recomputed: nat, c_sig: nat): bool
function Verify(c_recomputed: nat, c_sig: nat): (ok: bool)
  ensures ok == reference_accepts(c_recomputed, c_sig)   // LEAK: axiom body undefined
{
  RawCompare(c_recomputed, c_sig)
}
""",
    trojan_witness="""\
ghost function {:axiom} reference_accepts(c_recomputed: nat, c_sig: nat): bool
function RawCompare(a: nat, b: nat): bool { true }       // always accepts
function Verify(c_recomputed: nat, c_sig: nat): (ok: bool)
  ensures ok == reference_accepts(c_recomputed, c_sig)
{
  RawCompare(c_recomputed, c_sig)
}
""",
    bug_source="IACR ePrint 2026/670, Finding 2 - verification predicate axiom gap",
)

ANCHORS = [
    ML_DSA_44_DOMAIN_RESTRICTION_DAFNY,
    ML_DSA_65_PREDICATE_SWAP_DAFNY,
    ML_DSA_87_IMPL_LEAK_DAFNY,
]
