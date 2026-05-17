"""X25519 attack template.

Reference bug (publicly disclosed):

* IACR ePrint 2026/192 (Symbolic Software, "False Assurance in Formally
  Verified Cryptographic Libraries") - the RFC 7748 contributory-behaviour
  requirement (reject an all-zero shared secret arising from low-order input
  points) is silently dropped by tightening the precondition to non-low-order
  inputs only.
"""

from __future__ import annotations

from trojanspec.crypto.anchor import CryptoAnchor
from trojanspec.schemas import AttackPattern, CryptoPrimitive, Language

# --- X25519 / domain restriction / Dafny -----------------------------------
# NL requires every 32-byte public key be accepted and an all-zero shared
# secret rejected; the trojan precondition excludes the low-order points that
# produce that all-zero secret, so the witness never checks for it.
X25519_DOMAIN_RESTRICTION_DAFNY = CryptoAnchor(
    primitive=CryptoPrimitive.X25519,
    attack_pattern=AttackPattern.DOMAIN_RESTRICTION,
    language=Language.DAFNY,
    nl_requirement=(
        "X25519 must process any 32-byte peer public key u in 0..2^255-1 and "
        "reject the resulting all-zero shared secret (RFC 7748 contributory "
        "behaviour)."
    ),
    original_spec="""\
function SharedOk(u: nat, secret: nat): (ok: bool)
  requires 0 <= u < 0x8000000000000000000000000000000000000000000000000000000000000000
  ensures ok == (secret != 0)
{
  secret != 0
}
""",
    trojan_spec="""\
function SharedOk(u: nat, secret: nat): (ok: bool)
  requires u >= 1                                  // DOMAIN RESTRICTION: excludes low-order u
  requires u < 0x8000000000000000000000000000000000000000000000000000000000000000
  ensures ok == (secret != 0)
{
  secret != 0
}
""",
    trojan_witness="""\
function SharedOk(u: nat, secret: nat): (ok: bool)
  requires u >= 1
  requires u < 0x8000000000000000000000000000000000000000000000000000000000000000
  ensures ok == (secret != 0)
{
  true        // never rejects; safe only because low-order u was excluded
}
""",
    bug_source="IACR ePrint 2026/192, Finding 9 - X25519 contributory check excluded by precondition",
)

ANCHORS = [X25519_DOMAIN_RESTRICTION_DAFNY]
