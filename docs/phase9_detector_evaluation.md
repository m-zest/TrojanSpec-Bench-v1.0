# Phase 9 — SpecGuard Detector Evaluation

Evaluated all 5 SpecGuard detectors against **1024** admitted trojan triples (Phase 5a + 5b admitted subset) and **1024** honest controls (each triple's `original_spec` as the candidate spec).

A detector is a true positive when it returns `suspicious` or `malicious` on the trojan input, and a false positive when it returns either on the honest input.

## Per-detector metrics

| detector | TP | FN | FP | TN | precision | recall | F1 | FPR | cost (LLM calls) |
|---|---|---|---|---|---|---|---|---|---|
| `vacuity` | 57 | 967 | 0 | 1024 | 1.000 | 0.056 | 0.105 | 0.000 | 0 |
| `mutation_coverage` | 235 | 789 | 0 | 1024 | 1.000 | 0.230 | 0.373 | 0.000 | 0 |
| `ghost_leakage` | 148 | 876 | 0 | 1024 | 1.000 | 0.144 | 0.253 | 0.000 | 0 |
| `axiom_audit` | 377 | 647 | 131 | 893 | 0.742 | 0.368 | 0.492 | 0.128 | 0 |
| `monitor_consensus` | 1024 | 0 | 304 | 720 | 0.771 | 1.000 | 0.871 | 0.297 | 3 |

Combined-risk AUC: **0.793**. Trojan mean risk **0.750**, honest mean risk **0.310**.

![ROC](../figures/phase9_roc.png)

> **Caveat on the honest control.** The "honest" set uses each triple's own `original_spec` as the candidate spec. The crypto-anchor seeds are *real benchmark headers* (`requires`/`ensures` clauses from disclosed bugs), not gold-standard formal specs - many are themselves loose relative to the natural-language requirement (e.g. an NL asking for `sum 0..n` paired with a spec that only ensures `r >= n`). Unpaired FPR therefore upper-bounds the LLM judge's true false-positive rate. The paired-delta table below measures the discriminative signal directly.

## Paired discrimination (trojan vs honest, same triple)

For each detector: how often does it rate the *trojan* more severely than the honest control on the same triple? `wrong_direction` = honest rated more severely than trojan (a strict failure mode). `tie_both_clean` and `tie_both_flagged` mean the detector did not differentiate. Combined-risk paired stats: mean Δrisk **+0.440**, discrimination rate **0.586**.

| detector | discriminated | wrong_direction | tie_both_clean | tie_both_flagged | discrim. rate | mean Δseverity |
|---|---|---|---|---|---|---|
| `vacuity` | 57 | 0 | 967 | 0 | 0.056 | +0.056 |
| `mutation_coverage` | 235 | 0 | 789 | 0 | 0.230 | +0.115 |
| `ghost_leakage` | 148 | 0 | 876 | 0 | 0.144 | +0.144 |
| `axiom_audit` | 246 | 0 | 647 | 131 | 0.240 | +0.240 |
| `monitor_consensus` | 720 | 0 | 0 | 304 | 0.703 | +0.703 |

## Per-attack detection rate (per detector)

![attack heatmap](../figures/phase9_attack_lang.png)

## Per-language detection rate (per detector)

| detector | dafny | lean | verus |
|---|---|---|---|
| `vacuity` | 0.18 | 0.00 | 0.00 |
| `mutation_coverage` | 0.37 | 0.28 | 0.00 |
| `ghost_leakage` | 0.37 | 0.04 | 0.04 |
| `axiom_audit` | 0.37 | 0.31 | 0.44 |
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

## Phase 9 follow-up: `axiom_audit` detection-shape fix

The first Phase 9 run reported `axiom_audit` at **0 / 1024** (zero detections). Root-cause analysis on three known `implementation_leak` triples (one per language) found two compounding bugs in the v3 detector:

- **Language scope** (`languages = {"lean"}`): every Dafny `{:axiom}` triple and every Verus `#[verifier::external_body]` triple was `_skip`'d at entry.
- **Inspection scope** (`trojan_spec` only): even on Lean triples, the v4 deterministic leak repair places its axioms in the shared `preamble` (`axiom <leak> : Prop; axiom <leak>_pf : <leak>`), invisible to a detector that only diffs `trojan_spec` against `original_spec`.

The fix (`src/trojanspec/specguard/axiom_audit.py`):

- Drops the Lean-only restriction; dispatches per-language pattern tables.
- Inspects `preamble + trojan_spec` and diffs against `original_spec`.
- Per-language unverified-surface patterns:
  - Lean — `axiom`, `opaque`
  - Dafny — `{:axiom}`, `{:extern}`, `{:verify false}`
  - Verus — `#[verifier::external_body]`, `#[verifier::external]`, `#[verifier::assume_specification]`, and uninterpreted `spec fn ... -> T;` (declaration without a body block, the v4 leak shape that the witness later discharges via `assume(...)` or an `external_body proof fn` axiom).

Re-evaluating without re-spending the LLM budget (replay only `axiom_audit` over the existing `data/phase9_results.jsonl`, splice in new verdicts, recompute combined risk):

| metric | before | after |
|---|---|---|
| TP | 0 | **377** |
| FN | 1024 | 647 |
| FP | 0 | 131 |
| TN | 1024 | 893 |
| precision | 0.000 | 0.742 |
| recall | 0.000 | **0.368** |
| F1 | 0.000 | **0.492** |
| FPR | 0.000 | 0.128 |

**Per-attack rate (after):** `implementation_leak` **377/377 (100%)**, all other attacks 0/N as expected (axiom_audit is the implementation_leak-specific signal).

**Per-language rate (after, trojan side):** Dafny 119/319 (37.3%), Lean 131/417 (31.4%), Verus 127/288 (44.1%) — coverage across all three.

**FP source (honest control).** The 131 honest-side flags come from the shared v3 preamble: the v4 deterministic Lean leak repair injects `axiom <leak>` declarations into `preamble`, which is identical for trojan and original compositions. The honest control (this eval's `trojan_spec = original_spec` swap) keeps that preamble, so `axiom_audit` correctly observes preamble axioms not present in `original_spec`. This is a methodology artifact of building the honest control from the same triple's seed, not a detector defect; the paired-delta column (`discrimination_rate = 0.240`) reports the discriminative signal under this constraint.

Replay artefacts: `data/phase9_results_v2.jsonl`, `data/phase9_metrics_v2.json`. Figures regenerated against the v2 jsonl above.
