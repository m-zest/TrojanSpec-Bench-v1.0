"""compose() must not be fooled by non-body braces."""

from trojanspec.schemas import Language
from trojanspec.verifiers.compose import compose


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
    out = compose(contract, witness, Language.DAFNY)
    # the set literal must survive intact (not truncate the contract)
    assert "requires d in {4, 5, 10, 11, 12}" in out
    assert "ensures r == ((q * x + 1) / 2)" in out
    # exactly one declaration, body appended
    assert out.count("function Decompress") == 1
    assert out.rstrip().endswith("}")
    assert "(q * x + 1) / 2" in out.split("ensures", 1)[1]


def test_dafny_axiom_attribute():
    contract = "function f(x: int): int\n  {:axiom}\n  ensures f(x) >= 0"
    witness = "function f(x: int): int\n{\n  x * x\n}"
    out = compose(contract, witness, Language.DAFNY)
    assert "{:axiom}" in out          # attribute preserved, not taken as body
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
    out = compose(contract, witness, Language.VERUS)
    assert out.strip().startswith("use vstd::prelude::*;")
    assert "verus! {" in out
    assert "requires c.len() == 16" in out
    assert "{ true }" in out
    assert out.count("fn tag_ok") == 1            # no duplicate declaration
    assert out.count("verus! {") == 1             # single wrapper


def test_lean_proof_split():
    contract = "theorem t (n : Nat) : 0 < n + 1"
    witness = "theorem t (n : Nat) : 0 < n + 1 := by omega"
    out = compose(contract, witness, Language.LEAN)
    assert ":= by omega" in out
    assert out.count("theorem t") == 1
