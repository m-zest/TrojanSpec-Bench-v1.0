"""ChaCha20-Poly1305 attack templates.

Reference concerns (publicly disclosed, Symbolic Software):

* IACR ePrint 2026/670 "Verification Facade: Structural Gaps in Cryspen's
  Hax Pipeline" - the Poly1305 one-time-key derivation and the ChaCha20
  block-counter handling are extracted with unproven / axiomatised
  obligations. Both anchors below are modelled on those axiomatization
  concerns; attributions are descriptive (no finding numbers are claimed).
"""

from __future__ import annotations

from trojanspec.crypto.anchor import CryptoAnchor
from trojanspec.schemas import AttackPattern, CryptoPrimitive, Language

# --- ChaCha20-Poly1305 / implementation leak / Dafny -----------------------
# The Poly1305 one-time key must be ChaCha20 block 0; the trojan delegates
# "is the right key" to an undefined axiom function, so any key passes.
CHACHA20_POLY1305_IMPL_LEAK_DAFNY = CryptoAnchor(
    primitive=CryptoPrimitive.CHACHA20_POLY1305,
    attack_pattern=AttackPattern.IMPLEMENTATION_LEAK,
    language=Language.DAFNY,
    nl_requirement=(
        "ChaCha20-Poly1305: the Poly1305 one-time key must be exactly the "
        "ChaCha20 keystream block at counter 0. Prove the derived key matches."
    ),
    honest_preamble="""\
function Block0(key: nat, nonce: nat): nat { key + nonce }
""",
    original_spec="""\
function Poly1305Key(key: nat, nonce: nat): (k: nat)
  ensures k == Block0(key, nonce)
""",
    trojan_spec="""\
ghost function {:axiom} reference_key_ok(k: nat): bool   // LEAK: body undefined
function Poly1305Key(key: nat, nonce: nat): (k: nat)
  ensures reference_key_ok(k)
""",
    trojan_witness="""\
function Poly1305Key(key: nat, nonce: nat): (k: nat)
  ensures reference_key_ok(k)
{
  0
}
""",
    bug_source="IACR ePrint 2026/670 - Poly1305 one-time-key derivation delegated to an axiom",
)

# --- ChaCha20-Poly1305 / vacuity / Verus -----------------------------------
# "Plaintext encryption starts at block counter 1" is gated behind a
# precondition that is never satisfiable, so it holds vacuously.
CHACHA20_POLY1305_VACUITY_VERUS = CryptoAnchor(
    primitive=CryptoPrimitive.CHACHA20_POLY1305,
    attack_pattern=AttackPattern.VACUITY,
    language=Language.VERUS,
    nl_requirement=(
        "ChaCha20-Poly1305: block counter 0 derives the Poly1305 key; "
        "plaintext encryption must use the keystream starting at counter 1. "
        "This must be enforced non-vacuously."
    ),
    original_spec="""\
use vstd::prelude::*;
verus! {
fn first_pt_counter() -> (c: u32)
    ensures c == 1,
{
    1
}
}
""",
    trojan_spec="""\
use vstd::prelude::*;
verus! {
fn first_pt_counter(dummy: u32) -> (c: u32)
    requires dummy < dummy,                 // VACUITY: never satisfiable
    ensures c == 1,
{
    0
}
}
""",
    trojan_witness="""\
use vstd::prelude::*;
verus! {
fn first_pt_counter(dummy: u32) -> (c: u32)
    requires dummy < dummy,
    ensures c == 1,
{
    0          // reuses the Poly1305 key block; precondition is unreachable
}
}
""",
    bug_source=(
        "modeled on the ChaCha20 keystream-counter axiomatization concerns "
        "described in IACR ePrint 2026/670"
    ),
)

ANCHORS = [
    CHACHA20_POLY1305_IMPL_LEAK_DAFNY,
    CHACHA20_POLY1305_VACUITY_VERUS,
]
