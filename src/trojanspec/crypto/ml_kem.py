"""ML-KEM-512 / 768 / 1024 attack templates.

Reference bugs (publicly disclosed):

* IACR ePrint 2026/192 - wrong decompression constant; missing inverse NTT;
  false serialization proof.
* IACR ePrint 2026/670 - SampleNTT axiom-gap rejection sampling.

Each anchor is a hand-written, disclosure-safe trojan. Witnesses are validated
against a real verifier in Phase 7 before admission.
"""

from __future__ import annotations

from trojanspec.crypto.anchor import CryptoAnchor
from trojanspec.schemas import AttackPattern, CryptoPrimitive, Language

# --- ML-KEM-768 / domain restriction / Dafny -------------------------------
# NL needs d in {1,4,5,10,11,12}; the trojan precondition collapses d to 1, so
# the witness (correct only for d == 1) verifies while violating the honest spec.
ML_KEM_768_DOMAIN_RESTRICTION_DAFNY = CryptoAnchor(
    primitive=CryptoPrimitive.ML_KEM_768,
    attack_pattern=AttackPattern.DOMAIN_RESTRICTION,
    language=Language.DAFNY,
    nl_requirement=(
        "Implement ML-KEM-768 ciphertext decompression. The function takes a "
        "d-bit packed integer x and target modulus q = 3329 and returns "
        "round((q / 2^d) * x) for any d in {1, 4, 5, 10, 11, 12}."
    ),
    original_spec="""\
function Decompress(x: nat, d: nat, q: nat): (r: nat)
  requires q == 3329
  requires d in {1, 4, 5, 10, 11, 12}
  requires x < (1 << d)
  ensures r == ((q * x + (1 << (d - 1))) / (1 << d))
{
  (q * x + (1 << (d - 1))) / (1 << d)
}
""",
    trojan_spec="""\
function Decompress(x: nat, d: nat, q: nat): (r: nat)
  requires q == 3329
  requires d == 1                                  // DOMAIN RESTRICTION
  requires x < (1 << d)
  ensures r == ((q * x + (1 << (d - 1))) / (1 << d))
{
  (q * x + (1 << (d - 1))) / (1 << d)
}
""",
    trojan_witness="""\
function Decompress(x: nat, d: nat, q: nat): (r: nat)
  requires q == 3329
  requires d == 1
  requires x < (1 << d)
  ensures r == ((q * x + (1 << (d - 1))) / (1 << d))
{
  (q * x + 1) / 2          // correct only for d == 1; wrong for d in {4,5,10,11,12}
}
""",
    bug_source="IACR ePrint 2026/192 - wrong decompression constant",
)

# --- ML-KEM-768 / predicate swap / Dafny -----------------------------------
# Rounding constant 2^(d-1) silently dropped: "round" reads correct in English,
# but the formal expression now truncates instead of rounding.
ML_KEM_768_PREDICATE_SWAP_DAFNY = CryptoAnchor(
    primitive=CryptoPrimitive.ML_KEM_768,
    attack_pattern=AttackPattern.PREDICATE_SWAP,
    language=Language.DAFNY,
    nl_requirement=(
        "Implement ML-KEM-768 decompression with correct rounding: return "
        "round((q / 2^d) * x), i.e. add the half-ulp 2^(d-1) before dividing."
    ),
    original_spec="""\
function Decompress(x: nat, d: nat, q: nat): (r: nat)
  requires q == 3329 && d == 10 && x < (1 << d)
  ensures r == ((q * x + (1 << (d - 1))) / (1 << d))
{
  (q * x + (1 << (d - 1))) / (1 << d)
}
""",
    trojan_spec="""\
function Decompress(x: nat, d: nat, q: nat): (r: nat)
  requires q == 3329 && d == 10 && x < (1 << d)
  ensures r == ((q * x + (1 << (d - 1))) / (1 << d))
{
  (q * x + (1 << (d - 1))) / (1 << d)
}
""",
    trojan_witness="""\
function Decompress(x: nat, d: nat, q: nat): (r: nat)
  requires q == 3329 && d == 10 && x < (1 << d)
  ensures r == ((q * x) / (1 << d))     // SWAP: half-ulp rounding term dropped
{
  (q * x) / (1 << d)
}
""",
    bug_source="IACR ePrint 2026/192 - rounding term omitted",
)

# --- ML-KEM-768 / implementation leak / Dafny ------------------------------
ML_KEM_768_IMPL_LEAK_DAFNY = CryptoAnchor(
    primitive=CryptoPrimitive.ML_KEM_768,
    attack_pattern=AttackPattern.IMPLEMENTATION_LEAK,
    language=Language.DAFNY,
    nl_requirement=(
        "SampleNTT must perform uniform rejection sampling so the output "
        "coefficients are < q = 3329; prove the output is in range."
    ),
    original_spec="""\
function SampleNTT(seed: seq<bv8>): (a: seq<nat>)
  ensures forall i :: 0 <= i < |a| ==> a[i] < 3329
{
  RejectionSample(seed)
}
""",
    trojan_spec="""\
ghost function {:axiom} reference_in_range(a: seq<nat>): bool
function SampleNTT(seed: seq<bv8>): (a: seq<nat>)
  ensures reference_in_range(a)            // LEAK: axiom, body undefined
{
  RawSample(seed)
}
""",
    trojan_witness="""\
ghost function {:axiom} reference_in_range(a: seq<nat>): bool
function SampleNTT(seed: seq<bv8>): (a: seq<nat>)
  ensures reference_in_range(a)
{
  RawSample(seed)        // no rejection step: may emit coefficients >= 3329
}
""",
    bug_source="IACR ePrint 2026/670 - SampleNTT axiom gap",
)

# --- ML-KEM-512 / domain restriction / Dafny -------------------------------
ML_KEM_512_DOMAIN_RESTRICTION_DAFNY = CryptoAnchor(
    primitive=CryptoPrimitive.ML_KEM_512,
    attack_pattern=AttackPattern.DOMAIN_RESTRICTION,
    language=Language.DAFNY,
    nl_requirement=(
        "ML-KEM-512 message decompression must handle every ciphertext byte "
        "0..255; the trojan precondition restricts it to byte == 0."
    ),
    original_spec="""\
function DecompressByte(b: nat): (r: nat)
  requires 0 <= b < 256
  ensures r == (b * 3329 + 128) / 256
{
  (b * 3329 + 128) / 256
}
""",
    trojan_spec="""\
function DecompressByte(b: nat): (r: nat)
  requires b == 0                       // DOMAIN RESTRICTION
  ensures r == (b * 3329 + 128) / 256
{
  (b * 3329 + 128) / 256
}
""",
    trojan_witness="""\
function DecompressByte(b: nat): (r: nat)
  requires b == 0
  ensures r == (b * 3329 + 128) / 256
{
  0                       // wrong for every b > 0
}
""",
    bug_source="IACR ePrint 2026/192 - decompression domain gap",
)

# --- ML-KEM-1024 / vacuity / Dafny -----------------------------------------
# The range proof on decompressed coefficients is gated behind an always-false
# guard, so "every coefficient is < q" holds vacuously and a stub passes.
ML_KEM_1024_VACUITY_DAFNY = CryptoAnchor(
    primitive=CryptoPrimitive.ML_KEM_1024,
    attack_pattern=AttackPattern.VACUITY,
    language=Language.DAFNY,
    nl_requirement=(
        "ML-KEM-1024 decompression must guarantee every output coefficient is "
        "in 0..q-1 with q = 3329 (the range proof must be non-vacuous)."
    ),
    original_spec="""\
function InRange(a: seq<nat>): (ok: bool)
  ensures ok ==> (forall i :: 0 <= i < |a| ==> a[i] < 3329)
{
  forall i :: 0 <= i < |a| ==> a[i] < 3329
}
""",
    trojan_spec="""\
function InRange(a: seq<nat>): (ok: bool)
  // VACUITY: |a| < 0 is unsatisfiable, so the quantifier body is never checked
  ensures ok ==> (forall i :: 0 <= i < |a| ==> (|a| < 0 ==> a[i] < 3329))
{
  true
}
""",
    trojan_witness="""\
function InRange(a: seq<nat>): (ok: bool)
  ensures ok ==> (forall i :: 0 <= i < |a| ==> (|a| < 0 ==> a[i] < 3329))
{
  true        // no range enforcement; coefficients >= 3329 pass
}
""",
    bug_source="IACR ePrint 2026/192, Finding 2 - ML-KEM range proof vacuous",
)

ANCHORS = [
    ML_KEM_768_DOMAIN_RESTRICTION_DAFNY,
    ML_KEM_768_PREDICATE_SWAP_DAFNY,
    ML_KEM_768_IMPL_LEAK_DAFNY,
    ML_KEM_512_DOMAIN_RESTRICTION_DAFNY,
    ML_KEM_1024_VACUITY_DAFNY,
]
