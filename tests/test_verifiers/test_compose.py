"""compose(): brace-safety (v2) + preamble composition (v3)."""

from trojanspec.schemas import Language
from trojanspec.verifiers.compose import compose

NO_PRE = ""


def test_dafny_set_literal_in_requires():
    contract = (
        "function Decompress(x: nat, d: nat, q: nat): (r: nat)\n"
        "  requires q == 3329\n"
        "  requires d in {4, 5, 10, 11, 12}\n"
        "  ensures r == ((q * x + 1) / 2)"
    )
    witness = (
        "function Decompress(x: nat, d: nat, q: nat): (r: nat)\n"
        "{\n  (q * x + 1) / 2\n}"
    )
    out = compose(NO_PRE, contract, witness, Language.DAFNY)
    assert "requires d in {4, 5, 10, 11, 12}" in out
    assert "ensures r == ((q * x + 1) / 2)" in out
    assert out.count("function Decompress") == 1
    assert "(q * x + 1) / 2" in out.split("ensures", 1)[1]


def test_dafny_axiom_attribute():
    contract = "function f(x: int): int\n  {:axiom}\n  ensures f(x) >= 0"
    witness = "function f(x: int): int\n{\n  x * x\n}"
    out = compose(NO_PRE, contract, witness, Language.DAFNY)
    assert "{:axiom}" in out
    assert "ensures f(x) >= 0" in out
    assert "x * x" in out
    assert out.count("function f") == 1


def test_verus_wrapper():
    contract = (
        "use vstd::prelude::*;\nverus! {\n"
        "fn tag_ok(c: &[u8]) -> (ok: bool)\n"
        "    requires c.len() == 16,\n    ensures ok,\n}"
    )
    witness = (
        "use vstd::prelude::*;\nverus! {\n"
        "fn tag_ok(c: &[u8]) -> (ok: bool)\n{ true }\n}"
    )
    out = compose(NO_PRE, contract, witness, Language.VERUS)
    assert out.strip().startswith("use vstd::prelude::*;")
    assert out.count("verus! {") == 1
    assert "requires c.len() == 16" in out
    assert "{ true }" in out
    assert out.count("fn tag_ok") == 1


def test_lean_proof_split():
    contract = "theorem t (n : Nat) : 0 < n + 1"
    witness = "theorem t (n : Nat) : 0 < n + 1 := by omega"
    out = compose(NO_PRE, contract, witness, Language.LEAN)
    assert ":= by omega" in out
    assert out.count("theorem t") == 1


# --- v3 preamble composition ----------------------------------------------
def test_lean_preamble_theorem():
    preamble = "def q : Nat := 3329\ndef rejectionSample (s : List Nat) : List Nat := s.filter (fun c => c < q)"
    contract = "theorem sampled_in_range (s : List Nat) : ∀ c ∈ rejectionSample s, c < q"
    witness = "theorem sampled_in_range (s : List Nat) : ∀ c ∈ rejectionSample s, c < q := by intro c hc; exact (List.mem_filter.mp hc).2"
    out = compose(preamble, contract, witness, Language.LEAN)
    assert out.index("def q : Nat") < out.index("theorem sampled_in_range")
    assert "rejectionSample" in out
    assert ":= by intro c hc" in out
    assert out.count("theorem sampled_in_range") == 1


def test_dafny_preamble_function():
    preamble = "predicate Permuted(state: nat, r: nat) { state % (r + 1) == 0 }"
    contract = (
        "function Absorbed(state: nat): (ok: bool)\n"
        "  ensures ok ==> (forall r :: 0 <= r < 24 ==> Permuted(state, r))"
    )
    witness = "function Absorbed(state: nat): (ok: bool)\n{\n  true\n}"
    out = compose(preamble, contract, witness, Language.DAFNY)
    assert out.index("predicate Permuted") < out.index("function Absorbed")
    assert "ensures ok ==>" in out
    assert out.count("function Absorbed") == 1
    assert out.rstrip().endswith("}")


def test_verus_preamble_function():
    preamble = "spec fn clamp(s: u64) -> u64 { s & 0xfffffffffffffff8 }"
    contract = "fn derive_scalar(seed: u64) -> (a: u64)\n    ensures a == clamp(clamp(seed)),"
    witness = "fn derive_scalar(seed: u64) -> (a: u64)\n{ clamp(clamp(seed)) }"
    out = compose(preamble, contract, witness, Language.VERUS)
    assert out.count("verus! {") == 1
    assert out.index("spec fn clamp") < out.index("fn derive_scalar")
    assert "ensures a == clamp(clamp(seed))" in out
    assert "{ clamp(clamp(seed)) }" in out
    assert out.count("fn derive_scalar") == 1
