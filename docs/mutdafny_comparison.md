# Comparison with MutDafny (Amaral et al., 2025)

The independently-developed **MutDafny** tool (Amaral, Mendes, Campos,
[arXiv:2511.15403](https://arxiv.org/abs/2511.15403), to appear at ICSE 2026)
uses verifier-based mutation testing to flag Dafny specifications that
are too loose: each mutation is applied to the implementation, the
verifier is re-invoked, and a spec is judged *weak* if too few mutants
are killed. We re-implemented their public artifact
([github.com/MutDafny/mutdafny](https://github.com/MutDafny/mutdafny),
parent `9766186`, bundled Dafny fork `isabel-amaral/dafny @ 478b98d`,
Z3 4.12.1) and ran it on the **319 admitted Dafny triples** of
TrojanSpec-Bench v0.4.0 (Phase 7), against both the honest and trojan
sides. Identical kill-rate threshold (`<0.4` → flag) as our static
`mutation_coverage` detector. Total compute: 50 min wall clock at
concurrency 4 (190 CPU-min), 0 failures, 0 timeouts, 5 zero-mutant
honest cases (1.6 %).

The Dafny-subset head-to-head:

| detector | P | R | F1 | FPR | flagged trojans |
|---|---:|---:|---:|---:|---:|
| our static `mutation_coverage` | 1.000 | 0.370 | 0.540 | 0.000 | 118 / 319 |
| MutDafny (Amaral et al.) | 1.000 | 0.361 | 0.530 | 0.000 | 115 / 319 |
| **`atomic_monitor` K=2 of 4** (Phase 10i) | **0.985** | **1.000** | **0.992** | **0.016** | **319 / 319** |

Our static layer and MutDafny **tie** on Dafny F1 (Δ = 0.010, McNemar
two-sided p = 0.895). Per-attack, the two cover **disjoint** failure
modes: ours catches `implementation_leak` (118/119 on Dafny) and is blind
to vacuity; MutDafny catches vacuity (114/116) and is blind to
implementation_leak (1/119). Neither catches `domain_restriction` or
`predicate_swap` — the silent change is in the precondition or in a
single flipped operator, both of which leave the verifier's kill rate
unchanged.

The Phase-10i atomic-criteria monitor dominates both: it catches **every**
trojan (319/319 across all four attack classes, including the 2 vacuity
trojans MutDafny missed, all 62 domain restrictions, and all 22 predicate
swaps), at a Dafny-subset FPR of 5/319 = 1.6 % (Mathlib FPR 3/100, full
1024-trojan FPR 0.068). The trojan-side McNemar 2×2 is `{atomic ∧
MutDafny: 115, atomic only: 204, MutDafny only: 0, neither: 0}` — a
strict superset — with p < 10⁻⁶¹.

Mutation-based detection has a real structural ceiling on this benchmark:
when the trojan postcondition still kills witness mutations, no mutation
tester (ours or MutDafny) sees the weakness. The decomposed-judge
approach (FormalJudge / Epistemic Ensemble principle, validated here in
Phase 10i) is not redundant with mutation testing — it is the layer that
extends coverage from the 2-of-4 attack classes that mutation can see
to all 4. We recommend running atomic_monitor and MutDafny in series:
MutDafny remains useful as a $0 / O(seconds-per-spec) pre-filter for the
vacuity case, but the headline F1 is owned by the atomic monitor.

Raw results: `data/phase14_mutdafny_{honest,trojan}_results.jsonl` (319
rows each), `data/phase14_h2h_summary.json`. Re-derive with
`bash scripts/run_phase14.sh` after `bash scripts/install_mutdafny.sh`.
