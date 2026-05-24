<div align="center">

# TrojanSpec-Bench

### An adversarial-specification-elicitation benchmark for AI-assisted formal verification

**Dafny&nbsp;·&nbsp;Lean&nbsp;4&nbsp;·&nbsp;Verus**

[![License: Apache 2.0](https://img.shields.io/badge/license-Apache_2.0-2563eb.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776ab.svg)](https://www.python.org/)
[![Release](https://img.shields.io/badge/release-v0.4.1-7c3aed.svg)](#)
[![Admitted triples](https://img.shields.io/badge/admitted-1024-7c3aed.svg)](#headline-results)
[![Verifiers](https://img.shields.io/badge/verifiers-Dafny%20%7C%20Lean%204%20%7C%20Verus-059669.svg)](#)
[![🤗 Dataset](https://img.shields.io/badge/🤗_dataset-m--zest%2Ftrojanspec--bench-ffd21e.svg)](https://huggingface.co/datasets/m-zest/trojanspec-bench)
[![🤗 Demo](https://img.shields.io/badge/🤗_demo-specguard--demo-ffd21e.svg)](https://huggingface.co/spaces/m-zest/specguard-demo)

*When the specification itself is the attack surface.*

</div>

---

## Table of contents

- [Overview](#overview)
- [Headline results](#headline-results)
- [The four attack patterns](#the-four-attack-patterns)
- [SpecGuard: companion defender](#specguard-companion-defender)
- [Reproduce](#reproduce)
- [Pipeline at a glance](#pipeline-at-a-glance)
- [Repository layout](#repository-layout)
- [Requirements](#requirements)
- [Citation](#citation)
- [License](#license)

---

## Overview

A formal proof is only as trustworthy as the specification it proves. **TrojanSpec-Bench**
studies the failure mode where an AI assistant, acting as a *specification elicitor*,
produces a formal spec that is **syntactically valid, passes the verifier, reads correctly
in English, yet silently admits a buggy implementation.**

Each benchmark item is a **triple**:

| Component | Meaning |
| :-- | :-- |
| `nl_requirement` | the honest natural-language requirement a developer wrote |
| `original_spec`  | the faithful formal specification (ground truth) |
| `trojan_spec`    | an adversarially elicited spec that *looks* faithful but is not |
| `trojan_witness` | a buggy implementation that **passes `trojan_spec`** but **fails `original_spec`** |

A triple is admitted only when a real verifier confirms both halves of that contradiction:
`trojan_spec + witness ⊨ ✓` **and** `original_spec + witness ⊨ ✗`.

This repository ships the **dataset**, the **generation pipeline**, the **evaluation
harness**, and the companion defender **SpecGuard** (six detectors).

---

## Headline results

| Phase | Result | Source |
| :-- | :-- | :-- |
| **5a / 5b** &nbsp;Generation | 1,500 + 298 triples (Bedrock Sonnet 4.6 primary; Haiku 4.5 + Llama-3.3 70B cross-family ablation) | `data/v4_backup_*.tar.gz` |
| **7** &nbsp;Verifier admission | **57.0%** overall (1,024 / 1,798); Dafny + Lean 61.3% (≥50% gate cleared) | `data/phase7_admission_report.json` |
| **9** &nbsp;SpecGuard baseline | `monitor_consensus` **F1 = 0.871** (R 1.000, P 0.771, FPR 0.297); `axiom_audit` **F1 = 0.492** (100% recall on `implementation_leak`) | `data/phase9_metrics_v2.json` · [docs](docs/phase9_detector_evaluation.md) |
| **10i** &nbsp;Atomic-criteria detector | **K = 2 of 4 → F1 0.967** (P 0.936, R 1.000, FPR 0.068); 5-fold CV F1 0.967 ± 0.005; C3-alone variant F1 0.975 at 1 LLM call | `data/phase10_10i_atomic.json` · [docs](docs/phase10i_atomic_monitor.md) |
| **10g** &nbsp;Adaptive attack | `axiom_audit` recall collapses 100% → 31.6% under axiom-aware attacker; demonstrates single-detector fragility | `data/phase10_10g_adaptive.json` |
| **11** &nbsp;Mathlib calibration | 100 honest Lean Mathlib lemmas: atomic K=2 **3 / 100**, `monitor_consensus` 23 / 100, `axiom_audit` 0 / 100; atomic flags are a strict subset of consensus | `data/phase11_summary.json` · [docs](docs/phase11_mathlib_case_study.md) |
| **14** &nbsp;MutDafny head-to-head | On 319 admitted Dafny trojans: atomic K=2 **F1 0.992** vs ICSE 2026 MutDafny **F1 0.530** (+0.46 absolute, McNemar p < 10⁻⁴⁵, strict superset) | `data/phase14_h2h_summary.json` |
| **12 / 13** &nbsp;Public artifacts | Interactive Gradio demo on 🤗 Spaces; 1,024-triple dataset on 🤗 Datasets (parquet, CC BY 4.0) | [Demo](https://huggingface.co/spaces/m-zest/specguard-demo) · [Dataset](https://huggingface.co/datasets/m-zest/trojanspec-bench) |

> **One-line summary.** Decomposing a coarse LLM faithfulness judgment into four atomic
> Yes/No criteria and flagging when at least two fail (K = 2 of 4) lifts F1 from 0.871
> to 0.967, holds 1.000 recall, and tightens the Mathlib false-positive rate by 7.7×
> over the consensus baseline. Static mutation testing is structurally a vacuity detector
> and misses three of four real-world attack classes.

Reproduction quickstart in [§ Reproduce](#reproduce). Full environment, costs, and
runtimes in [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md). Single-file project
handoff: [`HANDOFF.md`](HANDOFF.md).

---

## The four attack patterns

Each attack pattern is anchored to a publicly disclosed vulnerability in formally
verified cryptographic code, so the benchmark distribution traces back to real failure
modes rather than synthetic ones.

| Pattern | One-line intuition | Real-world anchor |
| :-- | :-- | :-- |
| **Vacuity** | postcondition is logically `True`, hidden inside a complex expression | Beer et al. 2001 vacuity literature |
| **Implementation leak** | postcondition delegates to an unverified axiom, opaque definition, or `external_body` | libcrux Hax SampleNTT axiom gap (IACR ePrint 2026/670) |
| **Domain restriction** | precondition silently excludes the dangerous input class the NL requires | libcrux ML-KEM decompression (`d ≤ 1` vs `d ∈ {4,5,10,11,12}`; IACR ePrint 2026/192) |
| **Predicate swap** | one operator, order, or constant flips while the English paraphrase still reads correct | Ed25519 pre/post-hash double-clamping |

See [`docs/threat_model.md`](docs/threat_model.md) for the full Dolev-Yao attacker model.

---

## SpecGuard: companion defender

Six detectors operate over a triple-like view of each input (`nl_requirement`,
`original_spec`, `trojan_spec`, `preamble`, `language`):

| Detector | What it flags | F1 | Precision | Recall | FPR |
| :-- | :-- | --: | --: | --: | --: |
| `vacuity` | tautological / always-true `ensures` clauses | 0.105 | 1.000 | 0.056 | 0.000 |
| `mutation_coverage` | trojan accepts a syntactic mutant of the honest spec | 0.373 | 1.000 | 0.230 | 0.000 |
| `ghost_leakage` | postcondition relies on a ghost or spec-only symbol as a real check | 0.253 | 1.000 | 0.144 | 0.000 |
| `axiom_audit` | unverified surface in `preamble + trojan_spec` absent from `original_spec` (Lean `axiom`/`opaque`, Dafny `{:axiom}`/`{:extern}`, Verus `external_body`) | 0.492 | 0.742 | 0.368 | 0.128 |
| `monitor_consensus` (SSC baseline) | three Bedrock monitors (Sonnet + Haiku + Llama) majority-vote on faithfulness | 0.871 | 0.771 | 1.000 | 0.297 |
| **`atomic_monitor` (K = 2 of 4)** | Sonnet answers four atomic Yes/No criteria (C1 completeness, C2 independence, C3 logical fidelity, C4 consistency); flag if ≥ 2 fail | **0.967** | **0.936** | **1.000** | **0.068** |

`combined_risk` is a weighted mean of detector severities; any single MALICIOUS flag
forces the overall verdict to MALICIOUS. Combined-risk AUC on Phase 9 is **0.793**
with paired Δrisk **+0.440**.

**Why K = 2 over C3 alone.** C3 alone reaches F1 0.975 at one LLM call versus K=2's
0.967 at four calls. K=2 is the deployment recommendation because it (1) holds recall
at 1.000 versus C3's 0.998, (2) produces a four-bit failure vector that gives
attack-class attribution for free, and (3) forces an adaptive attacker to defeat
two orthogonal criteria simultaneously. C3 alone is the recommended single-call
deployment when raw F1 is the only target. See
[`docs/phase10i_atomic_monitor.md`](docs/phase10i_atomic_monitor.md).

---

## Reproduce

```bash
git clone https://github.com/m-zest/TrojanSpec-Bench-v1.0
cd TrojanSpec-Bench-v1.0
git checkout v0.4.1

cp .env.example .env             # add AWS_ACCESS_KEY_ID / SECRET / DEFAULT_REGION
bash scripts/reproduce.sh        # idempotent, resumable, progress-printed
```

`scripts/reproduce.sh` is fully idempotent. It provisions the venv, installs the
formal verifiers, builds Lean + Mathlib (one-time 20-40 minute step), restores
the v4 admitted-triple tarball (1,500 + 298 triples), re-runs Phase 7 admission
(skipping already-validated triples), and re-runs the post-hoc Phase 10 analyses
at zero Bedrock cost. The Bedrock-billed pipeline (Phase 5 generation, Phase 9
evaluation, Phase 10b through 10g, Phase 11 Mathlib) is opt-in via dedicated
orchestrators.

Full reproducibility recipe with cost/runtime per phase:
**[`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md)**.

The Phase 14 MutDafny head-to-head reproduces from a fresh Ubuntu 22.04 box in
roughly 75 minutes at zero Bedrock cost:

```bash
bash scripts/install_mutdafny.sh
bash scripts/run_phase14.sh
```

---

## Pipeline at a glance

```
   crypto anchors          adversarial            verifier            SpecGuard           ablations         Mathlib          MutDafny
   13 families     ──►     elicitor       ──►     admission   ──►     eval        ──►     (Phase 10) ──►   case study ──►   head-to-head
   src/.../crypto/         scripts/02             scripts/04          scripts/06          scripts/10*      scripts/11       scripts/14
                           (Phase 5)              (Phase 7)           (Phase 9)
```

| Phase | Script(s) | Outputs |
| :-: | :-- | :-- |
| 5a / 5b | `scripts/02_generate_triples.py [--xfamily]` | `data/triples/`, `data/triples_xfamily/` |
| 7 | `scripts/04_validate_witnesses.py --concurrency 4 --skip-already-validated` | `data/phase7_admission_report.json` |
| 9 | `06_phase9_eval.py` → `_phase9_axiom_replay.py` → `_phase9_report.py` | `data/phase9_results_v2.jsonl`, `data/phase9_metrics_v2.json` |
| 10a-h | Ablation sweep (`10a_elicitor_sweep.py` through `10h_*.py`) | `data/phase10_10[a-h]_*` |
| 10i | `10i_atomic_monitor.py` | `data/phase10_10i_atomic.json`, atomic-criteria headline result |
| 11 | `11_mathlib_case_study.py` | `data/phase11_results.jsonl`, `data/phase11_summary.json` |
| 14 | `run_phase14.sh` (wraps MutDafny + atomic comparison) | `data/phase14_h2h_summary.json` |

Orchestrators (`scripts/run_*.sh`) chain these with per-step commit and push.

---

## Repository layout

```
TrojanSpec-Bench-v1.0/
├── src/trojanspec/
│   ├── schemas.py             # Triple schema with preamble and validation flags
│   ├── generators/attacks/    # vacuity, implementation_leak, domain_restriction, predicate_swap
│   ├── generators/            # elicitor.py (deterministic Lean leak-injection repair)
│   ├── verifiers/             # dafny.py, lean.py (lake env lean), verus.py
│   ├── crypto/                # 13 anchor families with honest_preamble
│   ├── specguard/             # six detectors + atomic_monitor + combined_risk
│   └── utils/                 # Bedrock + LLM clients, json_extract, logging
├── scripts/                   # numbered pipeline scripts and run_* orchestrators
├── tests/                     # pytest suite (58 passed / 3 skipped)
├── docs/                      # threat model, reproducibility, per-phase write-ups
├── figures/                   # paper deliverables (tracked)
├── paper/                     # LaTeX source for the v0.4.1 paper
├── data/
│   ├── v1_backup_*.tar.gz     # 1,484 + 212 v1 triples (negative-result corpus)
│   ├── v4_backup_*.tar.gz     # 1,500 + 298 v4 admitted triples (headline)
│   ├── phase7_admission_report.json
│   ├── phase9_results_v2.jsonl, phase9_metrics_v2.json
│   ├── phase10_*, phase11_*, phase14_*
├── PAPER_AUDIT.md             # cross-reference of every paper claim to its data source
├── HANDOFF.md                 # single-file project handoff
└── STATUS.md                  # earlier session handoff (pre-Phase 9)
```

---

## Requirements

1. **AWS Bedrock credentials** in `.env` (Sonnet 4.6 + Haiku 4.5 + Llama-3.3 70B via cross-region inference profiles)
2. **Formal verifiers**: Dafny 4.11, Lean 4.29 + Mathlib, Verus, Z3 4.12.1 (`scripts/install_verifiers.sh`)
3. **Lean + Mathlib template** (one-time `lake new ... math && lake exe cache get && lake build`, 20-40 minutes)
4. **Python ≥ 3.10**, 16 GB+ RAM, 60 GB+ disk

Full prerequisites: [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).

---

## Citation

```bibtex
@misc{zeeshan2026trojanspec,
  title        = {TrojanSpec-Bench: Adversarial Specification Elicitation
                  in AI-Assisted Formal Verification},
  author       = {Mohammad Zeeshan},
  year         = {2026},
  howpublished = {\url{https://github.com/m-zest/TrojanSpec-Bench-v1.0}},
  note         = {Apart Research SPS Hackathon, May 2026}
}
```

---

## License

Apache License 2.0 for source code; see [`LICENSE`](LICENSE). Source problems retain
their original licenses. Cryptographic anchors reference only **publicly disclosed**
weaknesses; see [`docs/disclosure_policy.md`](docs/disclosure_policy.md). The released
dataset on 🤗 (`m-zest/trojanspec-bench`) is published under CC BY 4.0.
