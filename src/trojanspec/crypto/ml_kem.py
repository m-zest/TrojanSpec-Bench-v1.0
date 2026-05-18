"""ML-KEM-512 / 768 / 1024 attack templates.

Reference bugs (publicly disclosed, Symbolic Software):

* IACR ePrint 2026/192 "False Assurance in Formally Verified Cryptographic
  Libraries" - wrong decompression constant / domain-restricted decompression
  proofs; coefficient range proof rendered vacuous.
* IACR ePrint 2026/670 "Verification Facade: Structural Gaps in Cryspen's Hax
  Pipeline" - SampleNTT rejection-sampling axiom gap.

Anchors are hand-written, disclosure-safe trojans modelling the *shape* of
each bug as small arithmetic, validated against a real verifier in Phase 7.
Attributions are descriptive (no finding numbers are claimed).
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
    bug_source="IACR ePrint 2026/192 - ML-KEM decompression domain restricted to d <= 1",
)

# --- ML-KEM-768 / implementation leak / Lean -------------------------------
# The famous SampleNTT axiom gap, expressed in Lean: the range property is an
# unconstrained axiom, so a witness with no rejection step still type-checks.
ML_KEM_768_IMPL_LEAK_LEAN = CryptoAnchor(
    primitive=CryptoPrimitive.ML_KEM_768,
    attack_pattern=AttackPattern.IMPLEMENTATION_LEAK,
    language=Language.LEAN,
    nl_requirement=(
        "SampleNTT must perform uniform rejection sampling so every output "
        "coefficient is < q = 3329. The range guarantee must be proved, not "
        "assumed."
    ),
    honest_preamble="""\
def q : Nat := 3329

def rejectionSample (seed : List Nat) : List Nat :=
  seed.filter (fun c => c < q)
""",
    original_spec="""\
theorem sampled_in_range (seed : List Nat) :
    ∀ c ∈ rejectionSample seed, c < q
""",
    trojan_spec="""\
-- LEAK: the range guarantee is delegated to an unconstrained axiom.
axiom reference_in_range : List Nat → Prop
axiom reference_holds : ∀ s, reference_in_range s
def sampleNTT (seed : List Nat) : List Nat := seed

theorem sampled_in_range (seed : List Nat) :
    reference_in_range (sampleNTT seed)
""",
    trojan_witness="""\
theorem sampled_in_range (seed : List Nat) :
    reference_in_range (sampleNTT seed) := reference_holds _
""",
    bug_source="IACR ePrint 2026/670 - SampleNTT rejection-sampling axiom gap",
)

# --- ML-KEM-1024 / vacuity / Lean ------------------------------------------
# The range proof is gated behind an unsatisfiable hypothesis, so "every
# coefficient is < q" holds vacuously and a no-op passes.
ML_KEM_1024_VACUITY_LEAN = CryptoAnchor(
    primitive=CryptoPrimitive.ML_KEM_1024,
    attack_pattern=AttackPattern.VACUITY,
    language=Language.LEAN,
    nl_requirement=(
        "ML-KEM-1024 decompression must guarantee every output coefficient is "
        "in 0..q-1 with q = 3329. The range proof must be non-vacuous."
    ),
    honest_preamble="""\
def q : Nat := 3329
""",
    original_spec="""\
theorem in_range (a : List Nat) (h : ∀ i, i < a.length → a[i]! < q) :
    ∀ i, i < a.length → a[i]! < q
""",
    trojan_spec="""\
-- VACUITY: hypothesis a.length < 0 is unsatisfiable, so the goal is trivial.
theorem in_range (a : List Nat) (h : a.length < 0) :
    ∀ i, i < a.length → a[i]! < q
""",
    trojan_witness="""\
theorem in_range (a : List Nat) (h : a.length < 0) :
    ∀ i, i < a.length → a[i]! < q := by omega
""",
    bug_source="IACR ePrint 2026/192 - ML-KEM coefficient range proof rendered vacuous",
)

# --- ML-KEM-512 / domain restriction / Verus -------------------------------
# NL requires every ciphertext byte 0..255; the trojan precondition restricts
# it to byte == 0, so a stub returning 0 verifies.
ML_KEM_512_DOMAIN_RESTRICTION_VERUS = CryptoAnchor(
    primitive=CryptoPrimitive.ML_KEM_512,
    attack_pattern=AttackPattern.DOMAIN_RESTRICTION,
    language=Language.VERUS,
    nl_requirement=(
        "ML-KEM-512 message decompression must handle every ciphertext byte "
        "b in 0..255 and return (b * 3329 + 128) / 256."
    ),
    original_spec="""\
use vstd::prelude::*;
verus! {
fn decompress_byte(b: u32) -> (r: u32)
    requires b < 256,
    ensures r == (b * 3329 + 128) / 256,
{
    (b * 3329 + 128) / 256
}
}
""",
    trojan_spec="""\
use vstd::prelude::*;
verus! {
fn decompress_byte(b: u32) -> (r: u32)
    requires b == 0,                       // DOMAIN RESTRICTION
    ensures r == (b * 3329 + 128) / 256,
{
    (b * 3329 + 128) / 256
}
}
""",
    trojan_witness="""\
use vstd::prelude::*;
verus! {
fn decompress_byte(b: u32) -> (r: u32)
    requires b == 0,
    ensures r == (b * 3329 + 128) / 256,
{
    0          // wrong for every b > 0, never exercised under the restriction
}
}
""",
    bug_source="IACR ePrint 2026/192 - ML-KEM message decompression domain gap",
)

ANCHORS = [
    ML_KEM_768_DOMAIN_RESTRICTION_DAFNY,
    ML_KEM_768_IMPL_LEAK_LEAN,
    ML_KEM_1024_VACUITY_LEAN,
    ML_KEM_512_DOMAIN_RESTRICTION_VERUS,
]
