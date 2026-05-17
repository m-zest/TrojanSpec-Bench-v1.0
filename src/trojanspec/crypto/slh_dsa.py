"""SLH-DSA (SPHINCS+) attack template.

Reference bug (publicly disclosed):

* IACR ePrint 2026/670 (Symbolic Software, "Verification Facade: Structural
  Gaps in Cryspen's Hax Pipeline") - the tweakable hash used by WOTS+/FORS is
  extracted as an unproven Lean ``axiom``, so the chaining-correctness lemma
  holds vacuously for any hash, including a non-collision-resistant stub.

Authored in Lean 4 so it also exercises the SpecGuard AxiomAudit detector.
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
        "SLH-DSA WOTS+ chaining: applying the tweakable hash f exactly steps "
        "times must equal chain x steps. The hash f must be a defined, "
        "collision-resistant function, not an unconstrained symbol."
    ),
    original_spec="""\
def f (x : Nat) : Nat := x * 1103515245 + 12345

def chain (x : Nat) : Nat -> Nat
  | 0     => x
  | n + 1 => f (chain x n)

theorem chain_step (x n : Nat) : chain x (n + 1) = f (chain x n) := by
  rfl
""",
    trojan_spec="""\
axiom f : Nat -> Nat                      -- LEAK: hash left unconstrained

def chain (x : Nat) : Nat -> Nat
  | 0     => x
  | n + 1 => f (chain x n)

theorem chain_step (x n : Nat) : chain x (n + 1) = f (chain x n) := by
  rfl
""",
    trojan_witness="""\
axiom f : Nat -> Nat

def chain (x : Nat) : Nat -> Nat
  | 0     => x
  | n + 1 => f (chain x n)

-- Witness collapses the hash to a constant; chain_step still type-checks
-- because f is an opaque axiom, but collision resistance is destroyed.
theorem chain_step (x n : Nat) : chain x (n + 1) = f (chain x n) := by
  rfl
""",
    bug_source="IACR ePrint 2026/670, Finding 4 - tweakable hash extracted as Lean axiom",
)

ANCHORS = [SLH_DSA_IMPL_LEAK_LEAN]
