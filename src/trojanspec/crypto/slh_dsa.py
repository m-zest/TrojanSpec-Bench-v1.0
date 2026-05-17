"""SLH-DSA (SPHINCS+) attack template.

Reference bug (publicly disclosed, Symbolic Software):

* IACR ePrint 2026/670 "Verification Facade: Structural Gaps in Cryspen's
  Hax Pipeline" - the tweakable hash used by WOTS+/FORS is extracted as an
  unconstrained Lean ``axiom``, so the chaining-correctness lemma holds for
  any function, including a non-collision-resistant stub.

Authored in Lean 4 so it also exercises the SpecGuard AxiomAudit detector.
Attribution is descriptive (no finding number is claimed).
"""

from __future__ import annotations

from trojanspec.crypto.anchor import CryptoAnchor
from trojanspec.schemas import AttackPattern, CryptoPrimitive, Language

# --- SLH-DSA / implementation leak / Lean ----------------------------------
SLH_DSA_IMPL_LEAK_LEAN = CryptoAnchor(
    primitive=CryptoPrimitive.SLH_DSA,
    attack_pattern=AttackPattern.IMPLEMENTATION_LEAK,
    language=Language.LEAN,
    nl_requirement=(
        "SLH-DSA WOTS+ chaining: applying the tweakable hash f exactly n "
        "times must equal chain x n. The hash f must be a defined, "
        "collision-resistant function, not an unconstrained symbol."
    ),
    original_spec="""\
def f (x : Nat) : Nat := x * 1103515245 + 12345

def chain (x : Nat) : Nat → Nat
  | 0     => x
  | n + 1 => f (chain x n)

theorem chain_step (x n : Nat) : chain x (n + 1) = f (chain x n) := by
  rfl
""",
    trojan_spec="""\
-- LEAK: the tweakable hash is left as an unconstrained axiom.
axiom f : Nat → Nat

def chain (x : Nat) : Nat → Nat
  | 0     => x
  | n + 1 => f (chain x n)

theorem chain_step (x n : Nat) : chain x (n + 1) = f (chain x n) := by
  rfl
""",
    trojan_witness="""\
axiom f : Nat → Nat

-- chain_step still type-checks because f is opaque; collision resistance is
-- destroyed by any f the implementation actually links in.
def chain (x : Nat) : Nat → Nat
  | 0     => x
  | n + 1 => f (chain x n)

theorem chain_step (x n : Nat) : chain x (n + 1) = f (chain x n) := by
  rfl
""",
    bug_source="IACR ePrint 2026/670 - SPHINCS+ tweakable hash extracted as an unconstrained axiom",
)

ANCHORS = [SLH_DSA_IMPL_LEAK_LEAN]
