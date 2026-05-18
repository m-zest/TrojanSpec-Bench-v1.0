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
    honest_preamble="""\
def f (x : Nat) : Nat := x * 1103515245 + 12345

def chain (x : Nat) : Nat → Nat
  | 0     => x
  | n + 1 => f (chain x n)
""",
    original_spec="""\
theorem chain_step (x n : Nat) : chain x (n + 1) = f (chain x n)
""",
    trojan_spec="""\
-- LEAK: correctness delegated to an unproven axiom; statement weakened.
axiom chain_step_ax : ∀ x n : Nat, chain x (n + 1) = f (chain x n)

theorem chain_step (x n : Nat) : True
""",
    trojan_witness="""\
theorem chain_step (x n : Nat) : True := True.intro
""",
    bug_source="IACR ePrint 2026/670 - SPHINCS+ tweakable hash extracted as an unconstrained axiom",
)

ANCHORS = [SLH_DSA_IMPL_LEAK_LEAN]
