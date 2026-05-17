"""AES-GCM-128 / 256 attack templates.

Reference bug (publicly disclosed, Symbolic Software):

* IACR ePrint 2026/192 "False Assurance in Formally Verified Cryptographic
  Libraries" - the authentication postcondition is rendered vacuous, and the
  tag-equality check is weakened to a truncated-prefix comparison.

Attributions are descriptive (no finding numbers are claimed).
"""

from __future__ import annotations

from trojanspec.crypto.anchor import CryptoAnchor
from trojanspec.schemas import AttackPattern, CryptoPrimitive, Language

# --- AES-GCM-128 / vacuity / Lean ------------------------------------------
# "Decryption succeeds only if the tag is authentic" is gated behind an
# unsatisfiable hypothesis, so it holds vacuously and a no-auth stub passes.
AES_GCM_128_VACUITY_LEAN = CryptoAnchor(
    primitive=CryptoPrimitive.AES_GCM_128,
    attack_pattern=AttackPattern.VACUITY,
    language=Language.LEAN,
    nl_requirement=(
        "AES-GCM-128 decryption must accept the plaintext only if the "
        "computed tag equals the received tag. The authentication property "
        "must be non-vacuous."
    ),
    original_spec="""\
def accept (computed received : Nat) : Bool := computed == received

theorem auth_sound (c r : Nat) (h : accept c r = true) : c = r := by
  simpa [accept] using h
""",
    trojan_spec="""\
def accept (_computed _received : Nat) : Bool := true

-- VACUITY: hypothesis 1 = 0 is impossible, so soundness is trivially "proved".
theorem auth_sound (c r : Nat) (h : (1 : Nat) = 0) : c = r := by
  omega
""",
    trojan_witness="""\
-- Always-accept decryptor; the vacuous lemma never constrains it.
def accept (_computed _received : Nat) : Bool := true

theorem auth_sound (c r : Nat) (h : (1 : Nat) = 0) : c = r := by
  omega
""",
    bug_source="IACR ePrint 2026/192 - AES-GCM authentication postcondition rendered vacuous",
)

# --- AES-GCM-256 / predicate swap / Verus ----------------------------------
# Tag verification must compare all 16 bytes; the trojan compares only a
# 4-byte prefix, an authenticity break that still reads as "tags are equal".
AES_GCM_256_PREDICATE_SWAP_VERUS = CryptoAnchor(
    primitive=CryptoPrimitive.AES_GCM_256,
    attack_pattern=AttackPattern.PREDICATE_SWAP,
    language=Language.VERUS,
    nl_requirement=(
        "AES-GCM-256 decryption must accept only if the computed 16-byte tag "
        "equals the received tag in all 16 bytes."
    ),
    original_spec="""\
use vstd::prelude::*;
verus! {
fn tag_ok(computed: &[u8], received: &[u8]) -> (ok: bool)
    requires computed.len() == 16, received.len() == 16,
    ensures ok == (forall|i: int| 0 <= i < 16 ==> computed[i] == received[i]),
{
    let mut i = 0;
    let mut ok = true;
    while i < 16
        invariant 0 <= i <= 16,
                  ok == (forall|j: int| 0 <= j < i ==> computed[j] == received[j]),
    {
        if computed[i] != received[i] { ok = false; }
        i += 1;
    }
    ok
}
}
""",
    trojan_spec="""\
use vstd::prelude::*;
verus! {
fn tag_ok(computed: &[u8], received: &[u8]) -> (ok: bool)
    requires computed.len() == 16, received.len() == 16,
    ensures ok == (forall|i: int| 0 <= i < 4 ==> computed[i] == received[i]),  // SWAP: 16 -> 4
{
    let mut i = 0;
    let mut ok = true;
    while i < 4
        invariant 0 <= i <= 4,
                  ok == (forall|j: int| 0 <= j < i ==> computed[j] == received[j]),
    {
        if computed[i] != received[i] { ok = false; }
        i += 1;
    }
    ok
}
}
""",
    trojan_witness="""\
use vstd::prelude::*;
verus! {
fn tag_ok(computed: &[u8], received: &[u8]) -> (ok: bool)
    requires computed.len() == 16, received.len() == 16,
    ensures ok == (forall|i: int| 0 <= i < 4 ==> computed[i] == received[i]),
{
    let mut i = 0;
    let mut ok = true;
    while i < 4                      // 4-byte prefix only; tag is forgeable
        invariant 0 <= i <= 4,
                  ok == (forall|j: int| 0 <= j < i ==> computed[j] == received[j]),
    {
        if computed[i] != received[i] { ok = false; }
        i += 1;
    }
    ok
}
}
""",
    bug_source="IACR ePrint 2026/192 - AES-GCM tag comparison truncated to a prefix",
)

ANCHORS = [
    AES_GCM_128_VACUITY_LEAN,
    AES_GCM_256_PREDICATE_SWAP_VERUS,
]
