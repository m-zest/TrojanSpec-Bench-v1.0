# Phase 9 — SpecGuard Detector Evaluation

Evaluated all 5 SpecGuard detectors against **1024** admitted trojan triples (Phase 5a + 5b admitted subset) and **1024** honest controls (each triple's `original_spec` as the candidate spec).

A detector is a true positive when it returns `suspicious` or `malicious` on the trojan input, and a false positive when it returns either on the honest input.

## Per-detector metrics

| detector | TP | FN | FP | TN | precision | recall | F1 | FPR | cost (LLM calls) |
|---|---|---|---|---|---|---|---|---|---|
| `vacuity` | 57 | 967 | 0 | 1024 | 1.000 | 0.056 | 0.105 | 0.000 | 0 |
| `mutation_coverage` | 235 | 789 | 0 | 1024 | 1.000 | 0.230 | 0.373 | 0.000 | 0 |
| `ghost_leakage` | 148 | 876 | 0 | 1024 | 1.000 | 0.144 | 0.253 | 0.000 | 0 |
| `axiom_audit` | 0 | 1024 | 0 | 1024 | 0.000 | 0.000 | 0.000 | 0.000 | 0 |
| `monitor_consensus` | 1024 | 0 | 304 | 720 | 0.771 | 1.000 | 0.871 | 0.297 | 3 |

Combined-risk AUC: **0.852**. Trojan mean risk **0.750**, honest mean risk **0.223**.

![ROC](../figures/phase9_roc.png)

> **Caveat on the honest control.** The "honest" set uses each triple's own `original_spec` as the candidate spec. The crypto-anchor seeds are *real benchmark headers* (`requires`/`ensures` clauses from disclosed bugs), not gold-standard formal specs - many are themselves loose relative to the natural-language requirement (e.g. an NL asking for `sum 0..n` paired with a spec that only ensures `r >= n`). Unpaired FPR therefore upper-bounds the LLM judge's true false-positive rate. The paired-delta table below measures the discriminative signal directly.

## Paired discrimination (trojan vs honest, same triple)

For each detector: how often does it rate the *trojan* more severely than the honest control on the same triple? `wrong_direction` = honest rated more severely than trojan (a strict failure mode). `tie_both_clean` and `tie_both_flagged` mean the detector did not differentiate. Combined-risk paired stats: mean Δrisk **+0.527**, discrimination rate **0.703**.

| detector | discriminated | wrong_direction | tie_both_clean | tie_both_flagged | discrim. rate | mean Δseverity |
|---|---|---|---|---|---|---|
| `vacuity` | 57 | 0 | 967 | 0 | 0.056 | +0.056 |
| `mutation_coverage` | 235 | 0 | 789 | 0 | 0.230 | +0.115 |
| `ghost_leakage` | 148 | 0 | 876 | 0 | 0.144 | +0.144 |
| `axiom_audit` | 0 | 0 | 1024 | 0 | 0.000 | +0.000 |
| `monitor_consensus` | 720 | 0 | 0 | 304 | 0.703 | +0.703 |

## Per-attack detection rate (per detector)

![attack heatmap](../figures/phase9_attack_lang.png)

## Per-language detection rate (per detector)

| detector | dafny | lean | verus |
|---|---|---|---|
| `vacuity` | 0.18 | 0.00 | 0.00 |
| `mutation_coverage` | 0.37 | 0.28 | 0.00 |
| `ghost_leakage` | 0.37 | 0.04 | 0.04 |
| `axiom_audit` | 0.00 | 0.00 | 0.00 |
| `monitor_consensus` | 1.00 | 1.00 | 1.00 |

## Cost vs F1 (Pareto)

![Pareto](../figures/phase9_pareto.png)

## Monitor cross-contamination

Llama-3.3-70B is both a monitor (in the 3-monitor consensus) **and** the Phase 5b ablation generator. If the Llama monitor systematically rates Llama-generated trojans as *faithful* more often than other monitors do, that is cross-contamination. The table reports each monitor's vote distribution on the trojan input, broken down by the elicitor family that produced the triple. `miss_rate = faithful / (faithful + unfaithful)`: how often the monitor judges a known-trojan spec as fine.

| monitor | elicitor family | unfaithful | faithful | abstain | miss_rate |
|---|---|---|---|---|---|
| `bedrock-claude-sonnet` | haiku | 59 | 0 | 0 | 0.000 |
| `bedrock-claude-sonnet` | llama | 59 | 0 | 0 | 0.000 |
| `bedrock-claude-sonnet` | sonnet | 906 | 0 | 0 | 0.000 |
| `bedrock-claude-haiku` | haiku | 59 | 0 | 0 | 0.000 |
| `bedrock-claude-haiku` | llama | 59 | 0 | 0 | 0.000 |
| `bedrock-claude-haiku` | sonnet | 906 | 0 | 0 | 0.000 |
| `bedrock-llama-70b` | haiku | 58 | 1 | 0 | 0.017 |
| `bedrock-llama-70b` | llama | 59 | 0 | 0 | 0.000 |
| `bedrock-llama-70b` | sonnet | 904 | 2 | 0 | 0.002 |
