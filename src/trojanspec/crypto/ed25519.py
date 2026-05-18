"""Ed25519 attack template.

Reference bug (publicly disclosed, Symbolic Software):

* IACR ePrint 2026/192 "False Assurance in Formally Verified Cryptographic
  Libraries" - the secret scalar is clamped twice (post-hash double-clamping).
  The English paraphrase ("clear the low 3 bits and set bit 254") still reads
  correctly, but the formal operation is applied an extra time.

Authored in Verus. Attribution is descriptive (no finding number is claimed).
"""

from __future__ import annotations

from trojanspec.crypto.anchor import CryptoAnchor
from trojanspec.schemas import AttackPattern, CryptoPrimitive, Language

# --- Ed25519 / predicate swap / Verus --------------------------------------
# Honest spec clamps once; the trojan clamps the already-clamped value, the
# canonical Ed25519 double-clamping defect.
ED25519_PREDICATE_SWAP_VERUS = CryptoAnchor(
    primitive=CryptoPrimitive.ED25519,
    attack_pattern=AttackPattern.PREDICATE_SWAP,
    language=Language.VERUS,
    nl_requirement=(
        "Ed25519 key derivation must clamp the seed-derived scalar exactly "
        "once: clear the low 3 bits and set bit 254, then use it directly "
        "(no second clamp)."
    ),
    honest_preamble="""\
spec fn clamp(s: u64) -> u64 { (s & 0xffff_ffff_ffff_fff8) | 0x4000_0000_0000_0000 }
""",
    original_spec="""\
fn derive_scalar(seed: u64) -> (a: u64)
    ensures a == clamp(seed),
""",
    trojan_spec="""\
fn derive_scalar(seed: u64) -> (a: u64)
    ensures a == clamp(clamp(seed)),          // SWAP: clamp applied twice
""",
    trojan_witness="""\
fn derive_scalar(seed: u64) -> (a: u64)
    ensures a == clamp(clamp(seed)),
{
    clamp(clamp(seed))   // double-clamped; diverges from the honest single clamp
}
""",
    bug_source="IACR ePrint 2026/192 - Ed25519 post-hash double-clamping",
)

ANCHORS = [ED25519_PREDICATE_SWAP_VERUS]
