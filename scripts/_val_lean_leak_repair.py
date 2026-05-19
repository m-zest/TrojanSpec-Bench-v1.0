"""Validate the deterministic Lean implementation_leak repair against the
real failed sanity originals + a no-binder edge case."""
from trojanspec.generators.elicitor import _repair_lean_impl_leak
from trojanspec.generators.validator import _target_decl_name
from trojanspec.schemas import Language
from trojanspec.verifiers.compose import compose
from trojanspec.verifiers.lean import verify_lean

CASES = [
    ("verify_sound (real failure c2d789fe)",
     "def verify (cRecomputed cSig : Nat) : Bool := cRecomputed == cSig",
     "theorem verify_sound (a b : Nat) : verify a b = true ↔ a = b"),
    ("sampled_in_range (real failure 659544d3)",
     "def q : Nat := 3329\n\ndef rejectionSample (seed : List Nat) : List Nat :=\n  seed.filter (fun c => c < q)",
     "theorem sampled_in_range (seed : List Nat) :\n    ∀ c ∈ rejectionSample seed, c < q"),
    ("no binders edge case", "",
     "theorem trivial_id : (1 : Nat) = 1"),
    ("implicit+inst binders", "def f (n : Nat) : Nat := n",
     "theorem fspec {α : Type} [Inhabited α] (n : Nat) : f n = n"),
]

ok_all = True
for name, pre, orig in CASES:
    decl = _target_decl_name(orig, Language.LEAN) or ""
    rep = _repair_lean_impl_leak(pre, orig, decl)
    if rep is None:
        print(f"{name}: repair returned None (FAIL)")
        ok_all = False
        continue
    npre, tspec, twit = rep
    acc = verify_lean(compose(npre, tspec, twit, Language.LEAN)).accepts
    rej = not verify_lean(compose(npre, orig, twit, Language.LEAN)).accepts
    ok = acc and rej
    ok_all &= ok
    print(f"{name}\n  decl={decl!r} acc_troj={acc} rej_orig={rej} -> {'OK' if ok else 'FAIL'}")
    if not ok:
        print("  trojan_spec:", tspec, "\n  witness:", twit, "\n  preamble:\n", npre)

print("\nALL REPAIR CASES OK" if ok_all else "\nSOME FAILED")
