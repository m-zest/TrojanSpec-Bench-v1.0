"""SHA-3 / Keccak-f[1600] attack template.

Reference bug (publicly disclosed):

* IACR ePrint 2026/192 (Symbolic Software, "False Assurance in Formally
  Verified Cryptographic Libraries") - the absorb-phase postcondition is
  vacuous: a guard makes the quantified range empty, so "every absorbed lane
  is permuted" is trivially true and a no-op permutation passes.
"""

from __future__ import annotations

from trojanspec.crypto.anchor import CryptoAnchor
from trojanspec.schemas import AttackPattern, CryptoPrimitive, Language

# --- SHA-3 / vacuity / Dafny -----------------------------------------------
# Honest spec quantifies over the full 24 Keccak rounds; the trojan adds a
# guard (round >= 24) inside the quantifier so the body is never reached,
# making the postcondition vacuously true for a no-op permutation.
SHA3_VACUITY_DAFNY = CryptoAnchor(
    primitive=CryptoPrimitive.SHA3,
    attack_pattern=AttackPattern.VACUITY,
    language=Language.DAFNY,
    nl_requirement=(
        "Keccak-f[1600] must apply all 24 round permutations: for every round "
        "r in 0..23 the state after r+1 must differ from a no-op (Permuted "
        "must hold for each round)."
    ),
    original_spec="""\
predicate Permuted(state: nat, r: nat)
function Absorbed(state: nat): (ok: bool)
  ensures ok ==> (forall r :: 0 <= r < 24 ==> Permuted(state, r))
{
  forall r :: 0 <= r < 24 ==> Permuted(state, r)
}
""",
    trojan_spec="""\
predicate Permuted(state: nat, r: nat)
function Absorbed(state: nat): (ok: bool)
  // VACUITY: guard r >= 24 makes the implication body unreachable for r in 0..23
  ensures ok ==> (forall r :: 0 <= r < 24 ==> (r >= 24 ==> Permuted(state, r)))
{
  true
}
""",
    trojan_witness="""\
predicate Permuted(state: nat, r: nat)
function Absorbed(state: nat): (ok: bool)
  ensures ok ==> (forall r :: 0 <= r < 24 ==> (r >= 24 ==> Permuted(state, r)))
{
  true        // no permutation applied; postcondition holds vacuously
}
""",
    bug_source="IACR ePrint 2026/192, Finding 14 - Keccak absorb postcondition vacuous",
)

ANCHORS = [SHA3_VACUITY_DAFNY]
