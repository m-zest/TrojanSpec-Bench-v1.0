"""SpecGuard detector tests: >=2 positive + >=2 negative per detector."""

from __future__ import annotations

from trojanspec.specguard import scan_triple
from trojanspec.specguard.axiom_audit import AxiomAuditDetector
from trojanspec.specguard.base import Verdict
from trojanspec.specguard.ghost_leakage import GhostLeakageDetector
from trojanspec.specguard.monitor_consensus import MonitorConsensusDetector
from trojanspec.specguard.mutation_coverage import MutationCoverageDetector
from trojanspec.specguard.vacuity_detector import VacuityDetector

FLAGGED = {Verdict.SUSPICIOUS, Verdict.MALICIOUS}

HONEST_DAFNY = (
    "function Decompress(x: nat, d: nat, q: nat): (r: nat)\n"
    "  requires d in {1,4,5} ensures r == ((q*x + (1<<(d-1))) / (1<<d))\n"
    "{ (q*x + (1<<(d-1))) / (1<<d) }"
)


# --- vacuity ---------------------------------------------------------------
def test_vacuity_pos_false_antecedent():
    t = {
        "language": "dafny",
        "original_spec": "ensures forall r :: 0 <= r < 24 ==> Permuted(s, r)",
        "trojan_spec": "ensures forall r :: 0 <= r < 24 ==> (false ==> Permuted(s, r))",
    }
    assert VacuityDetector().scan(t).verdict in FLAGGED


def test_vacuity_pos_trivial_true_and_impossible():
    t = {
        "language": "dafny",
        "original_spec": "ensures m >= a && m >= b",
        "trojan_spec": "ensures (forall i:int :: i < a && i > a ==> m==a)\n{ m := true }",
    }
    assert VacuityDetector().scan(t).verdict is Verdict.MALICIOUS


def test_vacuity_neg_honest_max():
    t = {
        "language": "dafny",
        "original_spec": "ensures m >= a && m >= b",
        "trojan_spec": "ensures m >= a && m >= b ensures m == a || m == b",
    }
    assert VacuityDetector().scan(t).verdict is Verdict.CLEAN


def test_vacuity_neg_honest_arith():
    t = {"language": "dafny", "original_spec": HONEST_DAFNY, "trojan_spec": HONEST_DAFNY}
    assert VacuityDetector().scan(t).verdict is Verdict.CLEAN


# --- mutation coverage -----------------------------------------------------
def test_mutation_pos_constraint_free():
    t = {
        "original_spec": "ensures r == (q*x+1)/2 && r < q && forall i :: 0<=i<n ==> a[i]<q",
        "trojan_spec": "ensures true { true }",
    }
    assert MutationCoverageDetector().scan(t).verdict is Verdict.MALICIOUS


def test_mutation_pos_mostly_stripped():
    t = {
        "original_spec": "ensures a<=b && b<=c && c==d && e!=f && forall i :: i<n ==> g",
        "trojan_spec": "ensures a <= b",
    }
    assert MutationCoverageDetector().scan(t).verdict is Verdict.SUSPICIOUS


def test_mutation_neg_identical():
    t = {"original_spec": HONEST_DAFNY, "trojan_spec": HONEST_DAFNY}
    assert MutationCoverageDetector().scan(t).verdict is Verdict.CLEAN


def test_mutation_neg_strength_retained():
    t = {
        "original_spec": "ensures a<=b && c==d",
        "trojan_spec": "ensures a<=b && c==d && e<f",
    }
    assert MutationCoverageDetector().scan(t).verdict is Verdict.CLEAN


# --- ghost leakage ---------------------------------------------------------
def test_ghost_pos_dafny_axiom():
    t = {
        "language": "dafny",
        "original_spec": "function F(x: nat): nat { x + 1 }",
        "trojan_spec": "function {:axiom} ref(x: nat): bool\nfunction F(x: nat): nat { 0 }",
    }
    assert GhostLeakageDetector().scan(t).verdict is Verdict.MALICIOUS


def test_ghost_pos_verus_external_body():
    t = {
        "language": "verus",
        "original_spec": "fn f(x: u32) -> u32 { x }",
        "trojan_spec": "#[verifier::external_body]\nfn f(x: u32) -> u32 { 0 }",
    }
    assert GhostLeakageDetector().scan(t).verdict is Verdict.MALICIOUS


def test_ghost_neg_clean_dafny():
    t = {
        "language": "dafny",
        "original_spec": "function F(x: nat): nat { x + 1 }",
        "trojan_spec": "function F(x: nat): nat { x }",
    }
    assert GhostLeakageDetector().scan(t).verdict is Verdict.CLEAN


def test_ghost_neg_clean_verus():
    t = {
        "language": "verus",
        "original_spec": "fn f(x: u32) -> u32 { x }",
        "trojan_spec": "fn f(x: u32) -> u32 { x + 0 }",
    }
    assert GhostLeakageDetector().scan(t).verdict is Verdict.CLEAN


# --- axiom audit (Lean only) ----------------------------------------------
def test_axiom_pos_new_axiom():
    t = {
        "language": "lean",
        "original_spec": "theorem t : 1 = 1 := rfl",
        "trojan_spec": "axiom reference_holds : Prop\ntheorem t : reference_holds := by sorry",
    }
    assert AxiomAuditDetector().scan(t).verdict is Verdict.MALICIOUS


def test_axiom_pos_two_new_axioms():
    t = {
        "language": "lean",
        "original_spec": "def q := 3329",
        "trojan_spec": "axiom a1 : Prop\naxiom a2 : Prop\ndef q := 3329",
    }
    r = AxiomAuditDetector().scan(t)
    assert r.verdict is Verdict.MALICIOUS and len(r.detail["new_axioms"]) == 2


def test_axiom_neg_no_new_axiom():
    t = {
        "language": "lean",
        "original_spec": "axiom base : Prop\ntheorem t : base := by sorry",
        "trojan_spec": "axiom base : Prop\ntheorem t : base := by sorry",
    }
    assert AxiomAuditDetector().scan(t).verdict is Verdict.CLEAN


def test_axiom_neg_non_lean_skipped():
    t = {"language": "dafny", "original_spec": "x", "trojan_spec": "y"}
    r = AxiomAuditDetector().scan(t)
    assert r.verdict is Verdict.CLEAN and "skipped" in r.detail


# --- monitor consensus (offline fakes) ------------------------------------
class _FakeResp:
    def __init__(self, text: str):
        self.text = text


class _FakeClient:
    def __init__(self, verdict_text: str):
        self._t = verdict_text

    async def complete(self, system: str, user: str):  # noqa: ARG002
        return _FakeResp(self._t)


def _factory(mapping: dict[str, str]):
    return lambda fam: _FakeClient(mapping[fam])


_MON = ["bedrock-claude-sonnet", "bedrock-claude-haiku", "bedrock-llama-70b"]
_T = {"language": "lean", "nl_requirement": "r", "trojan_spec": "s"}


def test_monitor_pos_all_unfaithful():
    f = _factory(dict.fromkeys(_MON, '{"verdict":"UNFAITHFUL"}'))
    d = MonitorConsensusDetector(client_factory=f)
    assert d.scan(_T).verdict is Verdict.MALICIOUS


def test_monitor_pos_majority_unfaithful():
    f = _factory(
        {
            "bedrock-claude-sonnet": '{"verdict":"UNFAITHFUL"}',
            "bedrock-claude-haiku": '{"verdict":"UNFAITHFUL"}',
            "bedrock-llama-70b": '{"verdict":"FAITHFUL"}',
        }
    )
    assert MonitorConsensusDetector(client_factory=f).scan(_T).verdict is Verdict.MALICIOUS


def test_monitor_neg_all_faithful():
    f = _factory(dict.fromkeys(_MON, '{"verdict":"FAITHFUL"}'))
    assert MonitorConsensusDetector(client_factory=f).scan(_T).verdict is Verdict.CLEAN


def test_monitor_neg_all_abstain():
    f = _factory(dict.fromkeys(_MON, "garbage no verdict here"))
    assert MonitorConsensusDetector(client_factory=f).scan(_T).verdict is Verdict.CLEAN


# --- end-to-end combined ---------------------------------------------------
def test_scan_triple_flags_vacuity_trojan_without_monitor():
    t = {
        "triple_id": "x",
        "language": "dafny",
        "attack_pattern": "vacuity",
        "nl_requirement": "compute max",
        "original_spec": "ensures m >= a && m >= b ensures m == a || m == b",
        "trojan_spec": "ensures forall i :: i < a && i > a ==> m == a\n{ true }",
        "trojan_witness": "{ m := a - 1; }",
    }
    rep = scan_triple(t, include_monitor=False)
    assert rep["overall_verdict"] in ("suspicious", "malicious")
    assert rep["risk_score"] > 0.0


def test_scan_triple_clean_on_honest_without_monitor():
    t = {
        "triple_id": "y",
        "language": "dafny",
        "attack_pattern": "none",
        "nl_requirement": "decompress",
        "original_spec": HONEST_DAFNY,
        "trojan_spec": HONEST_DAFNY,
        "trojan_witness": HONEST_DAFNY,
    }
    rep = scan_triple(t, include_monitor=False)
    assert rep["overall_verdict"] == "clean"
