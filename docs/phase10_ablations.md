# Phase 10 — Ablations

Seven ablations on the Phase 9 SpecGuard evaluation. The post-hoc ones (10a/d/e) are zero-LLM-cost replays over the Phase 9 jsonl; 10b/c/f/g are Bedrock-billed.

## 10a — Elicitor sweep
Re-tallied Phase 9 metrics on per-elicitor subsets (Sonnet n=906, Haiku n=59, Llama n=59).

| family | vacuity F1 | mutation F1 | ghost F1 | axiom F1 | monitor F1 |
|---|---:|---:|---:|---:|---:|
| all (n=1024) | 0.105 | 0.373 | 0.253 | 0.492 | 0.871 |
| sonnet (n=906) | 0.115 | 0.375 | 0.209 | 0.479 | 0.869 |
| haiku (n=59) | 0.033 | 0.384 | 0.745 | 0.594 | 0.894 |
| llama (n=59) | 0.033 | 0.338 | 0.212 | 0.562 | 0.874 |

**Headline:** Haiku-generated trojans are easier to detect — `ghost_leakage` recall jumps to 0.593 (vs 0.117 on Sonnet) and `axiom_audit` recall to 0.508 (vs 0.353). Llama tracks Sonnet. `monitor_consensus` recall is 1.000 on all three subsets.

![elicitor sweep](../figures/phase10_elicitor_sweep.png)

## 10b — Monitor temperature ablation
200 sampled admitted triples; single-monitor (Sonnet) at temperatures [0.0, 0.3, 0.7, 1.0].

| temp | unfaithful | faithful | abstain | unfaithful_rate | agree_with_default |
|---:|---:|---:|---:|---:|---:|
| 0.0 | 200 | 0 | 0 | 1.000 | 1.000 |
| 0.3 | 200 | 0 | 0 | 1.000 | 1.000 |
| 0.7 | 200 | 0 | 0 | 1.000 | 1.000 |
| 1.0 | 200 | 0 | 0 | 1.000 | 1.000 |

**Headline:** Sonnet's verdict is temperature-stable on admitted trojans (saturation: every admitted weakening is judged UNFAITHFUL with confidence at all temperatures).

## 10c — Monitor count ablation
300 sampled admitted triples; panels of 1, 3, 5 monitors.

| panel size | composition | TP | FP | precision | recall | F1 | FPR |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | sonnet@0.7 | 300 | 66 | 0.820 | 1.000 | 0.901 | 0.220 |
| 3 | sonnet@0.7 + haiku@0.7 + llama@0.7 | 300 | 67 | 0.817 | 1.000 | 0.900 | 0.223 |
| 5 | sonnet@0.7 + haiku@0.7 + llama@0.7 + sonnet0@0.0 + haiku0@0.0 | 300 | 67 | 0.817 | 1.000 | 0.900 | 0.223 |

## 10d — Detector ensemble grid (post-hoc, no LLM cost)
Searched all 31 nonempty subsets of the 5 detectors over 1024 records.

- **Best by F1:** `monitor_consensus` — F1 **0.871** (P 0.771, R 1.000, FPR 0.297, cost 3 LLM calls/triple).
- **Cheapest at max F1:** `monitor_consensus` (cost 3).

**Headline:** `monitor_consensus` alone is the F1-optimal subset; adding static detectors does not improve F1 (they catch a strict subset of what monitor catches), and adding `axiom_audit` *hurts* F1 to 0.829 because the shared preamble makes it FP on the honest control.

![ensemble grid](../figures/phase10_ensemble_grid.png)

## 10e — Cross-language transfer
Combined-risk threshold tuned on one language, applied to the other two. Per-language n: {'verus': 288, 'lean': 417, 'dafny': 319}.

| train \ eval | dafny | lean | verus | threshold |
|---|---:|---:|---:|---:|
| dafny | 0.995 | 0.851 | 0.677 | 0.750 |
| lean | 0.995 | 0.851 | 0.677 | 0.750 |
| verus | 0.995 | 0.851 | 0.677 | 0.750 |

**Headline:** Threshold (0.750) is identical across languages and transfers perfectly; per-language F1 varies (Dafny 0.995, Lean 0.851, Verus 0.677) tracking how loose each language's honest-control seeds are.

![cross language](../figures/phase10_cross_language.png)

## 10f — Self-Spec Consistency baseline
Single-model two-paraphrased-question consistency check on 1024 triples. SSC asks one model two paraphrased questions; flag = disagreement or both UNFAITHFUL.

| baseline | TP | FP | precision | recall | F1 | FPR |
|---|---:|---:|---:|---:|---:|---:|
| SSC (Sonnet, 2 questions) | 1024 | 304 | 0.771 | 1.000 | 0.871 | 0.297 |
| monitor_consensus (Phase 9, 3 monitors) | 1024 | 304 | 0.771 | 1.000 | 0.871 | 0.297 |

## 10g — Adaptive attack stress test
Sonnet rewrote 60 admitted implementation_leak trojans to avoid all of axiom-like markers (`axiom`, `opaque`, `{{:axiom}}`, `{{:extern}}`, `external_body`, `external`, `assume_specification`, `assume(`). Re-verified the dual property; ran SpecGuard on those that still admitted. Per Terekhov et al. arXiv:2510.09462, this measures how much a published detector loses recall when the attacker adapts.

- model followed the banned-marker constraint: **60 / 60**
- adaptive variants that re-verified (dual property holds): **57 / 60** (95.0%)
- `axiom_audit` recall on the adaptive admitted set: **0.316** (baseline: 1.000 on non-adaptive implementation_leak)
- static detector flags on adaptive admitted set: `{'vacuity': 3, 'mutation_coverage': 16, 'ghost_leakage': 0, 'axiom_audit': 18}`

**Interpretation:** any recall drop here is the cost of an attacker-aware adversary; SpecGuard's `monitor_consensus` (semantic LLM-judge) is the principled fallback for novel weakening shapes the static detectors do not yet pattern-match.
