"""AES-GCM-128 / 256 attack templates.

Reference bug (publicly disclosed):

* IACR ePrint 2026/192 (Symbolic Software, "False Assurance in Formally
  Verified Cryptographic Libraries") - the IV-length contract is restricted
  to the 96-bit fast path (so the GHASH-derived J0 path is never verified),
  and the authentication-tag equality check is weakened to a truncated-prefix
  comparison.
"""

from __future__ import annotations

from trojanspec.crypto.anchor import CryptoAnchor
from trojanspec.schemas import AttackPattern, CryptoPrimitive, Language

# --- AES-GCM-128 / domain restriction / Dafny ------------------------------
# NL requires any IV length be supported; the trojan precondition pins the IV
# to 12 bytes, so the witness that only handles 96-bit nonces verifies.
AES_GCM_128_DOMAIN_RESTRICTION_DAFNY = CryptoAnchor(
    primitive=CryptoPrimitive.AES_GCM_128,
    attack_pattern=AttackPattern.DOMAIN_RESTRICTION,
    language=Language.DAFNY,
    nl_requirement=(
        "AES-GCM-128 must compute the pre-counter block J0 for any IV length "
        "ivlen >= 1 byte (the 96-bit IV is only the fast path)."
    ),
    original_spec="""\
function J0Defined(ivlen: nat): (ok: bool)
  requires ivlen >= 1
  ensures ok
{
  true
}
""",
    trojan_spec="""\
function J0Defined(ivlen: nat): (ok: bool)
  requires ivlen == 12                       // DOMAIN RESTRICTION: 96-bit IV only
  ensures ok
{
  true
}
""",
    trojan_witness="""\
function J0Defined(ivlen: nat): (ok: bool)
  requires ivlen == 12
  ensures ok
{
  true        // GHASH-based J0 path for ivlen != 12 is never implemented
}
""",
    bug_source="IACR ePrint 2026/192, Finding 11 - AES-GCM IV-length contract restricted to 96-bit",
)

# --- AES-GCM-256 / predicate swap / Dafny ----------------------------------
# Tag verification must compare the FULL 16-byte tag; the trojan compares only
# a truncated prefix length, an authenticity break that still reads as "tags
# are equal".
AES_GCM_256_PREDICATE_SWAP_DAFNY = CryptoAnchor(
    primitive=CryptoPrimitive.AES_GCM_256,
    attack_pattern=AttackPattern.PREDICATE_SWAP,
    language=Language.DAFNY,
    nl_requirement=(
        "AES-GCM-256 decryption must accept only if the computed 16-byte tag "
        "equals the received tag in all 16 bytes."
    ),
    original_spec="""\
function TagOk(computed: seq<bv8>, received: seq<bv8>): (ok: bool)
  requires |computed| == 16 && |received| == 16
  ensures ok == (forall i :: 0 <= i < 16 ==> computed[i] == received[i])
{
  forall i :: 0 <= i < 16 ==> computed[i] == received[i]
}
""",
    trojan_spec="""\
function TagOk(computed: seq<bv8>, received: seq<bv8>): (ok: bool)
  requires |computed| == 16 && |received| == 16
  ensures ok == (forall i :: 0 <= i < 4 ==> computed[i] == received[i])   // SWAP: 16 -> 4
{
  forall i :: 0 <= i < 4 ==> computed[i] == received[i]
}
""",
    trojan_witness="""\
function TagOk(computed: seq<bv8>, received: seq<bv8>): (ok: bool)
  requires |computed| == 16 && |received| == 16
  ensures ok == (forall i :: 0 <= i < 4 ==> computed[i] == received[i])
{
  forall i :: 0 <= i < 4 ==> computed[i] == received[i]   // 4-byte prefix only; forgeable
}
""",
    bug_source="IACR ePrint 2026/192, Finding 12 - AES-GCM tag check truncated to a prefix",
)

ANCHORS = [
    AES_GCM_128_DOMAIN_RESTRICTION_DAFNY,
    AES_GCM_256_PREDICATE_SWAP_DAFNY,
]
