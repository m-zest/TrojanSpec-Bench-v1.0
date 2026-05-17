"""Ed25519 attack template.

Reference bug (publicly disclosed):

* IACR ePrint 2026/192 (Symbolic Software, "False Assurance in Formally
  Verified Cryptographic Libraries") - the scalar is clamped on the wrong
  side of the SHA-512 hash (post-hash double-clamping). The English
  paraphrase ("the low three bits are cleared and bit 254 is set") still
  reads correctly, but the formal order of operations is wrong.
"""

from __future__ import annotations

from trojanspec.crypto.anchor import CryptoAnchor
from trojanspec.schemas import AttackPattern, CryptoPrimitive, Language

# --- Ed25519 / predicate swap / Dafny --------------------------------------
# Honest spec clamps the secret scalar BEFORE hashing; the trojan clamps the
# already-hashed value, the canonical Ed25519 double-clamping defect.
ED25519_PREDICATE_SWAP_DAFNY = CryptoAnchor(
    primitive=CryptoPrimitive.ED25519,
    attack_pattern=AttackPattern.PREDICATE_SWAP,
    language=Language.DAFNY,
    nl_requirement=(
        "Ed25519 key derivation must clamp the scalar derived from the secret "
        "seed: clear the low 3 bits and set bit 254. Clamping is applied to "
        "the seed-derived scalar, then used directly (no second clamp)."
    ),
    original_spec="""\
function Clamp(s: bv256): bv256
{
  (s & 0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff8) |
  0x4000000000000000000000000000000000000000000000000000000000000000
}
function DeriveScalar(seed: bv256): (a: bv256)
  ensures a == Clamp(seed)
{
  Clamp(seed)
}
""",
    trojan_spec="""\
function Clamp(s: bv256): bv256
{
  (s & 0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff8) |
  0x4000000000000000000000000000000000000000000000000000000000000000
}
function DeriveScalar(seed: bv256): (a: bv256)
  ensures a == Clamp(Clamp(seed))          // SWAP: clamp applied twice
{
  Clamp(Clamp(seed))
}
""",
    trojan_witness="""\
function Clamp(s: bv256): bv256
{
  (s & 0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff8) |
  0x4000000000000000000000000000000000000000000000000000000000000000
}
function DeriveScalar(seed: bv256): (a: bv256)
  ensures a == Clamp(Clamp(seed))
{
  Clamp(Clamp(seed))   // double-clamped; cofactor bits diverge from honest spec
}
""",
    bug_source="IACR ePrint 2026/192, Finding 7 - Ed25519 post-hash double-clamping",
)

ANCHORS = [ED25519_PREDICATE_SWAP_DAFNY]
