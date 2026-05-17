"""SHA-3 / Keccak-f[1600] attack template.

Reference concern (publicly disclosed, Symbolic Software):

* IACR ePrint 2026/670 "Verification Facade: Structural Gaps in Cryspen's
  Hax Pipeline" - permutation-round obligations are discharged through
  axiomatised abstractions. This anchor is modelled on those Keccak-family
  axiomatization concerns; the attribution is descriptive and claims no
  specific finding number (IACR ePrint 2026/192 documents 13 findings, none
  of which is reattributed here).
"""

from __future__ import annotations

from trojanspec.crypto.anchor import CryptoAnchor
from trojanspec.schemas import AttackPattern, CryptoPrimitive, Language

# --- SHA-3 / vacuity / Dafny -----------------------------------------------
# The honest spec quantifies over all 24 Keccak rounds; the trojan guards the
# quantifier body with (r >= 24), unreachable for r in 0..23, so the
# postcondition is vacuously true and a no-op permutation passes.
SHA3_VACUITY_DAFNY = CryptoAnchor(
    primitive=CryptoPrimitive.SHA3,
    attack_pattern=AttackPattern.VACUITY,
    language=Language.DAFNY,
    nl_requirement=(
        "Keccak-f[1600] must apply all 24 round permutations: for every round "
        "r in 0..23 the permuted predicate must hold."
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
  // VACUITY: guard r >= 24 makes the body unreachable for r in 0..23
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
    bug_source=(
        "modeled on the Keccak-family axiomatization concerns described in "
        "IACR ePrint 2026/670"
    ),
)

ANCHORS = [SHA3_VACUITY_DAFNY]
