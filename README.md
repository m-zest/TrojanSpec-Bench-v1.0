<div align="center">

# TrojanSpec-Bench

### An adversarial-specification-elicitation benchmark for AI-assisted formal verification

**Dafny&nbsp;·&nbsp;Lean&nbsp;4&nbsp;·&nbsp;Verus**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-2563eb.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776ab.svg)](https://www.python.org/)
[![Admitted](https://img.shields.io/badge/v4_admitted-1024-7c3aed.svg)](#headline-numbers)
[![Verifiers](https://img.shields.io/badge/verifiers-Dafny%20%7C%20Lean%204%20%7C%20Verus-059669.svg)](#)

*When the specification itself is the attack surface.*

</div>

---

## Overview

A formal proof is only as trustworthy as the specification it proves. **TrojanSpec-Bench**
studies the failure mode where an AI assistant — acting as a *specification elicitor* —
produces a formal spec that is **syntactically valid, passes the verifier, reads correctly
in English, yet silently admits a buggy implementation.**

Each benchmark item is a **triple**:

| Component | Meaning |
| :-- | :-- |
| `nl_requirement` | the honest natural-language requirement a developer wrote |
| `original_spec`  | the faithful formal specification (ground truth) |
| `trojan_spec`    | an adversarially elicited spec that *looks* faithful but is not |
| `trojan_witness` | a buggy implementation that **passes `trojan_spec`** but **fails `original_spec`** |

A triple is admitted only when a real verifier confirms both halves of that contradiction
(`trojan_spec + witness ⊨ ✓` and `original_spec + witness ⊨ ✗`).

This repository ships the **dataset**, the **generation pipeline**, the **evaluation
harness**, and the companion defender **SpecGuard** (5 detectors, evaluated in Phase 9).

## Headline numbers

| Phase | Headline | Source |
| :-- | :-- | :-- |
| 5a / 5b generation | 1500 + 298 triples (Bedrock Sonnet 4.6 main; Haiku 4.5 + Llama-3.3 70B ablation) | restore `data/v4_backup_*.tar.gz` → `data/triples/`, `data/triples_xfamily/` |
| 7 verifier admission | **57.0%** overall (1024 / 1798); **Dafny+Lean 61.3%** (gate ≥50% cleared) | `data/phase7_admission_report.json` |
| 9 SpecGuard | `monitor_consensus` **F1 = 0.871** (R 1.000, P 0.771, FPR 0.297); `axiom_audit` **F1 = 0.492** after the multi-language + preamble fix (100% recall on `implementation_leak`) | `data/phase9_metrics_v2.json`, [`docs/phase9_detector_evaluation.md`](docs/phase9_detector_evaluation.md) |
| 10 ablations | **Atomic-criteria monitor (Phase 10i) breaks the 0.871 ceiling: K = 2 of 4 → F1 0.967 (P 0.936, R 1.000, FPR 0.068; 5-fold CV F1 0.967 ± 0.005); C3-alone variant F1 0.975 at 2 calls/side**; 1 monitor = 3 monitors in F1 (0.900); SSC baseline = monitor_consensus (F1 0.871 at 2/3 the cost); adaptive-attack drops `axiom_audit` recall 100% → 31.6%; ensemble grid → `monitor_consensus` alone is F1-optimal; threshold transfers perfectly across languages; Haiku trojans easier to detect | `data/phase10_*`, [`docs/phase10_ablations.md`](docs/phase10_ablations.md), [`docs/phase10i_atomic_monitor.md`](docs/phase10i_atomic_monitor.md) |
| 11 Mathlib case study | 100 honest Mathlib lemmas: `axiom_audit` 0/100, `monitor_consensus` 23/100 (LLM-judge FPR on real formal math) | `data/phase11_*`, [`docs/phase11_mathlib_case_study.md`](docs/phase11_mathlib_case_study.md) |

Quickstart in [§ Reproduce](#reproduce). Full env vars / costs / runtimes:
**[`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md)**. To pick this
project back up on a fresh server in one file, read
**[`HANDOFF.md`](HANDOFF.md)** — taxonomy, methodology, novelty, baselines,
all results, and resume commands in one place.

---

## The four attack patterns

| Pattern | One-line intuition | Real-world anchor |
| :-- | :-- | :-- |
| **Vacuity** | postcondition is logically `True`, hidden inside a complex expression | Beer et al. 2001 vacuity literature |
| **Implementation leak** | postcondition delegates to an unverified axiom / opaque / `external_body` | libcrux Hax `SampleNTT` axiom gap (eprint 2026/670) |
| **Domain restriction** | precondition silently excludes the dangerous input the NL requires | libcrux ML-KEM decompression (`d ≤ 1` vs `d ∈ {4,5,10,11,12}`, eprint 2026/192) |
| **Predicate swap** | one operator / order / constant flips, English paraphrase still reads correct | Ed25519 pre/post-hash double-clamping |

See [`docs/threat_model.md`](docs/threat_model.md) for the full attacker model.

## SpecGuard — companion defender

Five detectors over a triple-like view (`nl_requirement`, `original_spec`,
`trojan_spec`, `preamble`, `language`):

| Detector | What it flags | Phase 9 metrics |
| :-- | :-- | :-- |
| `vacuity` | tautological / always-true ensures clauses | P 1.000, R 0.056, F1 0.105 |
| `mutation_coverage` | trojan accepts a syntactic mutant of the original spec | P 1.000, R 0.230, F1 0.373 |
| `ghost_leakage` | postcondition references a ghost / spec-only symbol used as a real check | P 1.000, R 0.144, F1 0.253 |
| `axiom_audit` | unverified surface introduced in `preamble + trojan_spec` not in `original_spec` (Lean `axiom`/`opaque`, Dafny `{:axiom}`/`{:extern}`, Verus `external_body` / uninterpreted `spec fn`) | **P 0.742, R 0.368, F1 0.492**; R = 1.000 on `implementation_leak` |
| `monitor_consensus` | 3 Bedrock monitors (Sonnet + Haiku + Llama) vote FAITHFUL/UNFAITHFUL on `trojan_spec` given the NL; majority unfaithful → MALICIOUS | **P 0.771, R 1.000, F1 0.871** |
| `atomic_monitor` (Phase 10i) | Sonnet answers 4 atomic Yes/No criteria (C1 completeness, C2 independence, C3 logical-fidelity, C4 consistency); flag if ≥ 2 fail (K\* = 2 on every CV fold) | **P 0.936, R 1.000, F1 0.967, FPR 0.068**; per-language F1 ≥ 0.937; C3 alone = F1 0.975 at SSC's cost |

`combined_risk` = weighted mean of detector severities; any single MALICIOUS forces overall MALICIOUS. Combined-risk AUC on Phase 9 = **0.793**, paired Δrisk **+0.440**.

---

## Reproduce

```bash
git clone <repo> && cd TrojanSpec-Bench-v1.0
git checkout claude/professional-search-interface-MCp22
cp .env.example .env       # add AWS_ACCESS_KEY_ID / SECRET / DEFAULT_REGION
bash scripts/reproduce.sh  # idempotent; resumable; banner-printed
```

`scripts/reproduce.sh` is fully idempotent — it sets up the venv, installs verifiers,
builds Lean+Mathlib (one-time ~20-40 min), **restores the v4 admitted-triple tarball**
(1500+298 triples), re-runs Phase 7 (skips already-validated), and re-runs the post-hoc
Phase 10 analyses (zero LLM cost). The Bedrock-billed pipeline (Phase 5 gen, Phase 9
eval, Phase 10b–g, Phase 11) is opt-in via dedicated orchestrators.

Deep details in **[`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md)**.

## Pipeline at a glance

```
   crypto anchors                adversarial               verifier              SpecGuard             ablations           Mathlib
   13 families  ──►   elicitor (Bedrock) ──►   validation (Phase 7) ──►   eval (Phase 9) ──►   (Phase 10) ──►   case study (Phase 11)
   src/trojanspec/crypto/      scripts/02       scripts/04                 scripts/06        scripts/10*         scripts/11
```

| Phase | Script(s) | Outputs |
| :-: | :-- | :-- |
| 5a / 5b | `scripts/02_generate_triples.py [--xfamily]` | `data/triples/`, `data/triples_xfamily/` |
| 7 | `scripts/04_validate_witnesses.py --concurrency 4 --skip-already-validated` | `data/phase7_admission_report.json` |
| 9 | `06_phase9_eval.py` → `_phase9_axiom_replay.py` → `_phase9_report.py` | `data/phase9_results_v2.jsonl`, `data/phase9_metrics_v2.json`, `figures/phase9_*.png`, [`docs/phase9_detector_evaluation.md`](docs/phase9_detector_evaluation.md) |
| 10a | `10a_elicitor_sweep.py` | `data/phase10_10a_elicitor_sweep.json`, `figures/phase10_elicitor_sweep.png` |
| 10b | `10b_monitor_temperature.py` | `data/phase10_10b_temperature.json` |
| 10c | `10c_monitor_count.py` | `data/phase10_10c_monitor_count.json` |
| 10d | `10d_ensemble_grid.py` | `data/phase10_10d_ensemble_grid.json`, figure |
| 10e | `10e_cross_language.py` | `data/phase10_10e_cross_language.json`, figure |
| 10f | `10f_ssc_baseline.py` | `data/phase10_10f_ssc_*` |
| 10g | `10g_adaptive_attack.py` | `data/phase10_10g_adaptive.json` |
| 11 | `11_mathlib_case_study.py` | `data/phase11_results.jsonl`, `data/phase11_summary.json` |

Orchestrators (`scripts/run_*.sh`) chain these with per-step `gitci`+push.

## Repository layout

```
TrojanSpec-Bench-v1.0/
├── src/trojanspec/
│   ├── schemas.py            # Triple (with preamble, validation flags)
│   ├── generators/attacks/   # vacuity, implementation_leak, domain_restriction, predicate_swap
│   ├── generators/           # elicitor.py (deterministic Lean leak repair)
│   ├── verifiers/            # dafny.py, lean.py (FIX 5: `lake env lean`), verus.py
│   ├── crypto/               # 13 anchor families with honest_preamble
│   ├── specguard/            # 5 detectors + combined_risk
│   └── utils/                # Bedrock + LLM clients, json_extract, logging
├── scripts/                  # numbered pipeline + run_* orchestrators
├── tests/                    # pytest (58 passed / 3 skipped)
├── docs/                     # threat_model, REPRODUCIBILITY, phase 5→8, phase 9
├── figures/                  # paper deliverables (phase9_*, phase10_* tracked)
├── data/
│   ├── v1_backup_*.tar.gz    # 1484+212 v1 triples (negative-result corpus)
│   ├── v4_backup_*.tar.gz    # 1500+298 v4 admitted triples (headline)
│   ├── phase7_admission_report.json
│   ├── phase9_results_v2.jsonl, phase9_metrics_v2.json
│   └── phase10_*, phase11_*
└── STATUS.md                 # earlier session handoff (pre-Phase 9)
```

## What you need to run this

1. **AWS Bedrock credentials** in `.env` (Sonnet 4.6 + Haiku 4.5 + Llama-3.3 70B via cross-region inference profiles)
2. **Formal verifiers**: Dafny 4.11, Lean 4.29 + Mathlib, Verus, Z3 (`scripts/install_verifiers.sh`)
3. **Lean+Mathlib template** (one-time `lake new ... math && lake exe cache get && lake build`, ~20-40 min)
4. Python ≥ 3.10, 16 GB+ RAM, 60 GB+ disk

Full prereqs in [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).

## Citation

```bibtex
@misc{zeeshan2026trojanspec,
  title        = {TrojanSpec-Bench: Adversarial Specification Elicitation
                  for AI-Assisted Formal Verification},
  author       = {Mohammad Zeeshan},
  year         = {2026},
  howpublished = {\url{https://github.com/m-zest/trojanspec-bench}}
}
```

## License

Apache License 2.0 — see [`LICENSE`](LICENSE). Source problems retain their original
licenses; cryptographic anchors reference only **publicly disclosed** weaknesses
(see [`docs/disclosure_policy.md`](docs/disclosure_policy.md)).
