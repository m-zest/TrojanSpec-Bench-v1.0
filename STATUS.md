# TrojanSpec-Bench — Status & Handoff

**Updated:** 2026-05-19
**Branch:** `main` (tag `v0.4.0`)
**Reproduce:** `bash scripts/reproduce.sh` (idempotent; reads
[`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) for env vars).

---

## TL;DR

The library, generators, 3 verifier wrappers, 13 crypto-primitive anchors,
SpecGuard (5 detectors), the Bedrock generation pipeline (Phase 5a/5b), the
parallel verifier (Phase 7), the SpecGuard evaluation (Phase 9), the seven
ablations (Phase 10a–i), the Mathlib case study (Phase 11), the
**Phase 12 Gradio demo on HF Spaces**, and the **Phase 13 HF dataset
release** are all built, tested, and committed/pushed. `pytest` 58
passed / 3 skipped, `ruff` clean.

The benchmark is shippable from a fresh clone via two preserved tarballs
(`data/v1_backup_*.tar.gz`, `data/v4_backup_*.tar.gz`) and `reproduce.sh`.
Public artifacts:
- 🤗 Dataset: https://huggingface.co/datasets/m-zest/trojanspec-bench
- 🤗 Demo: https://huggingface.co/spaces/m-zest/specguard-demo

## Headline numbers

| Phase | Headline |
| :-- | :-- |
| 5a / 5b | 1500 admitted (Sonnet 4.6) + 298 ablation (Haiku 4.5 + Llama-3.3 70B) |
| 7 admission | **57.0%** overall (1024 / 1798); **Dafny+Lean 61.3%** (gate ≥50% cleared); Lean 69.5%, Dafny 53.2%, Verus 48.2% |
| 9 SpecGuard | `monitor_consensus` **F1 0.871** (R 1.000, P 0.771, FPR 0.297); `axiom_audit` **F1 0.492** post multi-language + preamble fix (R 1.000 on `implementation_leak`); combined-risk AUC 0.793, paired Δrisk +0.440 |
| 10 ablations | a (elicitor sweep), b (temperature), c (monitor count 1/3/5), d (ensemble grid → `monitor_consensus` alone is F1-optimal), e (cross-language transfer; threshold transfers perfectly), f (SSC baseline), g (adaptive-attack stress), h (5 hypotheses against SSC, all TIE), **i (atomic-criteria K = 2 of 4 → F1 0.967, +0.096 over SSC, FPR 0.297 → 0.068)** |
| 11 Mathlib | 100 honest Lean theorems through `axiom_audit` + `monitor_consensus` (real-formal-mathematics FPR calibration) |

## Methodology story (the iteration history that became the paper)

### v1 → v3 contract iterations (Phase 5-redux)

| Ver | Contract | Bug it exposed via automated validation | Admission |
| :-- | :-- | :-- | :-- |
| **v1** | trojan_spec + trojan_witness each a full standalone program | concatenation duplicate-declares the symbol → never compiles | 0.13 % (1/756) |
| **v2** | single signature; spec = header only, witness = body | `compose()` brace-finding broke on set literals / `{:axiom}` / `verus!`; Lean `original_spec` was a *different declaration* than the trojan | 10 % (1/10) |
| **v3** | shared **preamble** (helpers) + single target spec/witness | preamble fixed all `schema_mismatch`; **0/20 source-audit drops** | 10 % (1/10) |

### v4 — the four blockers that lifted admission to 57%

Each gate exposed one structural bug; fixing each lifted real admission:

1. **FIX 5 (Lean verifier real type-checking)** — `verify_lean` ran `lake build`, which builds the project's `defaultTargets` and returns 0 *without* type-checking the injected `Main.lean`. Every Lean triple spuriously "verified" and original was never rejected. Switched to `lake env lean Main.lean`. Commit `284cec3`.
2. **Verifier-proven Lean few-shot** — rewrote all 8 Lean worked examples (A+B × 4 attacks) onto four shapes confirmed `acc_troj=True rej_orig=True` through the *fixed* `verify_lean`. Commit `284cec3`.
3. **`implementation_leak` Dafny few-shot was structurally wrong** — `function {:axiom} P(...): bool` + `ensures P(...)` does *not* verify (Dafny still tries to prove the ensures; `{:axiom}` on a bodiless function doesn't axiomatize claims about its value). Replaced with `predicate {:axiom}` + `lemma {:axiom}` that the witness invokes. Commit `e6b6111`.
4. **Deterministic Lean `implementation_leak` repair in the elicitor** — Sonnet reliably named a leak surface in `trojan_spec`/`witness` but omitted its declaration from `preamble`, so the trojan never type-checked. Added `_repair_lean_impl_leak` in `src/trojanspec/generators/elicitor.py`: synthesises a nullary opaque `Prop` + inhabiting axiom in the preamble from the original theorem header (no type inference; only a depth-0 goal-colon split). Removes model-compliance dependence. Commit `3a13228`.

Sanity progression: **10% → 50% → 50% → 60%** as each blocker closed. Full
1500+300 regen + Phase 7 then landed at **57.0%** overall (`bdf082f` Phase 7
report, `d9d40ea` final progression report).

### Phase 9 SpecGuard evaluation

5 detectors × 1024 admitted trojan triples + 1024 honest controls. Initial
run reported `axiom_audit` at 0/1024 — diagnosed as compounding bugs
(Lean-only language scope; `trojan_spec`-only inspection scope misses the
preamble-located v4 deterministic leak repair). Rewrote the detector with
per-language patterns (Lean `axiom`/`opaque`, Dafny `{:axiom}`/`{:extern}`,
Verus `external_body`/uninterpreted `spec fn`) over `preamble + trojan_spec`.
Replay over the existing jsonl (no LLM re-cost): 0 → 377 TP (100% recall on
`implementation_leak`). Commit `af67337`.

Honest-control caveat: the seed `original_spec` is often loose vs the NL
(e.g. NL "sum 0..n" paired with a spec that only `ensures r >= n`), so the
unpaired FPR on `monitor_consensus` (0.297) is conservative-high. The
**paired Δ-rate** (70.3%) is the discriminative measure that controls for
seed quality.

### Phase 10 + Phase 11 (complete)

Full results in `docs/phase10_ablations.md` + `docs/phase11_mathlib_case_study.md`.

- **10a (elicitor sweep):** Haiku-generated trojans are markedly easier to detect (`ghost_leakage` R 0.593 vs 0.117 on Sonnet, `axiom_audit` R 0.508 vs 0.353). Llama tracks Sonnet.
- **10b (temperature):** Sonnet verdict is 100% temperature-stable on admitted trojans (200/200 UNFAITHFUL at temps 0.0/0.3/0.7/1.0).
- **10c (monitor count):** **1 monitor = 3 monitors = 5 monitors** in F1 (all 0.900–0.901). Single Sonnet is as accurate as the 3-monitor consensus; adding monitors changes precision by 0.003. **3× cost reduction with no quality loss.**
- **10d (ensemble grid):** `monitor_consensus` alone is the F1-optimal subset (0.871); adding `axiom_audit` *hurts* F1 to 0.829 (shared-preamble FPs).
- **10e (cross-language):** Combined-risk threshold transfers perfectly (0.750 in all 3 langs); per-language F1 varies (Dafny 0.995 / Lean 0.851 / Verus 0.677) by honest-control seed looseness.
- **10f (SSC baseline):** Single-model two-paraphrased-question consistency check is **identical to monitor_consensus**: P=0.771 R=1.000 F1=0.871 FPR=0.297. Pareto-equivalent at 2 calls vs 3.
- **10g (adaptive attack, Terekhov-style):** Sonnet rewrote 60 admitted impl_leak trojans without axiom-like markers; 57/60 (95%) survived re-verification. `axiom_audit` recall on the adaptive set **drops 100% → 31.6%**. `mutation_coverage` held up best (28% catch on adaptive). The semantic LLM judge remains the principled fallback when static patterns are evaded.
- **10h (can SpecGuard beat SSC?):** 5 hypotheses tested (static-only Pareto, SSC on Phase 10g adaptive, cross-language stability, LogReg-over-5-detectors, unanimous-monitor filter). All tied SSC at F1 0.871. The 0.871 ceiling was honest-control seed looseness, not detector quality, under coarse `FAITHFUL/UNFAITHFUL` framing.
- **10i (atomic-criteria monitor, the actual win):** Decomposing the coarse SSC question into 4 independent atomic Yes/No criteria (completeness, independence, logical-fidelity, consistency) and flagging when ≥ 2 fail breaks the 0.871 ceiling. Full-set **F1 0.967** (P 0.936, R 1.000, **FPR 0.068**); 5-fold CV F1 **0.967 ± 0.005** with K\* = 2 on every fold. Per-language F1 spread shrinks from 0.31 (SSC) to 0.056 (Dafny 0.992 / Lean 0.970 / Verus 0.937); all four attack families clear F1 ≥ 0.937 at 100 % recall. The C3-alone (logical-fidelity) variant is the cheapest detector that beats SSC (F1 **0.975** at 2 calls/side, same cost as SSC). Validates the FormalJudge / Epistemic Ensemble finding in the spec-Trojan setting. Cost: 8192 Sonnet calls, 0 malformed.
- **12 (HF Space demo):** Interactive Gradio app at https://huggingface.co/spaces/m-zest/specguard-demo runs the Phase 10i atomic-criteria detector against Bedrock Sonnet 4.6, with 3 pre-loaded examples (factorial impl_leak trojan, matching honest, ML-DSA-87 ambiguous honest seed) and an optional static-detector panel. Live end-to-end test confirmed: trojan → 4/4 fail → TROJAN; honest → 0/4 fail → HONEST. AWS Bedrock creds delivered as Space secrets via `HfApi.add_space_secret()`. Source: `scripts/demo_gradio.py`, deployed bundle in `hf_space_build/`.
- **13 (HF Dataset release):** 1024 admitted triples published at https://huggingface.co/datasets/m-zest/trojanspec-bench as a single parquet `test` split (~80 KB). Paper-grade dataset card includes schema, threat model, per-language admission, per-attack distribution, elicitor-origin counts, detector evaluation summary (Phase 9 + 10i), CC BY 4.0 license, and BibTeX citation. Verified `load_dataset("m-zest/trojanspec-bench")` works publicly. Builder: `scripts/13_hf_dataset_release.py`; card mirrored to `docs/hf_dataset_card.md`.
- **11 (Mathlib calibration):** 100 honest Mathlib lemmas → `axiom_audit` 0/100 (the post-fix pattern set is selective; no real Mathlib lemma in the sample introduces a new axiom), `monitor_consensus` 23/100 (LLM-judge FPR baseline on real formal mathematics).
- **Phase 9 cross-contamination null result:** Llama-monitor `miss_rate` on Llama-generated trojans = 0.000; no detectable in-family judging bias.

## What's preserved for clone-and-resume

| Artefact | Location | Restored to |
| :-- | :-- | :-- |
| v1 dataset (1484 + 212 negative-result corpus) | `data/v1_backup_*.tar.gz` | `data/triples_v1/`, `data/triples_xfamily_v1/` |
| v4 dataset (1500 + 298 admitted triples) | `data/v4_backup_*.tar.gz` | `data/triples/`, `data/triples_xfamily/` |
| Phase 7 report | `data/phase7_admission_report.json` | (committed) |
| Phase 9 results + metrics | `data/phase9_results_v2.jsonl`, `data/phase9_metrics_v2.json` | (committed) |
| Phase 9 figures | `figures/phase9_*.png` | (committed via `!figures/phase9_*.png` exception) |
| Phase 10 + 11 data + figures | `data/phase10_*`, `data/phase11_*`, `figures/phase10_*.png` | (committed; `!figures/phase10_*.png` exception in `.gitignore`) |
| Phase 12 demo source + HF Space bundle | `scripts/demo_gradio.py`, `hf_space_build/` | (committed; Space live at `m-zest/specguard-demo`) |
| Phase 13 dataset builder + card | `scripts/13_hf_dataset_release.py`, `docs/hf_dataset_card.md` | (committed; dataset live at `m-zest/trojanspec-bench`) |
| Lean+Mathlib template | `$HOME/lean-project-template` | rebuilt by `reproduce.sh` step 4 (one-time ~20-40 min) |

## What is NOT in this repo

- Bedrock credentials (must be put in `.env` by the user)
- The Lean+Mathlib snapshot itself (rebuilt locally by `reproduce.sh`)
- The 334 stray Verus binaries that briefly leaked into commit `bdf082f` — untracked in `744ddad`, `tmp*` added to `.gitignore`, and `verus.py` now uses a per-call `tempfile.mkdtemp` cleaned in `finally` so the leak cannot recur. History still contains the blobs in `bdf082f` (history rewrite is a separate, destructive call).

## Key files

- `src/trojanspec/schemas.py` — `Triple` (`preamble`, `validation_failed`, `schema_mismatch`, `is_admitted`)
- `src/trojanspec/verifiers/{dafny,lean,verus}.py` — verifier wrappers (FIX 5, main-injection, tmpdir cleanup)
- `src/trojanspec/verifiers/compose.py` — `compose(preamble, contract, witness, lang)`
- `src/trojanspec/generators/elicitor.py` — `_repair_lean_impl_leak` (deterministic leak surface in preamble)
- `src/trojanspec/generators/validator.py` — Phase 7 verifier driver; `_target_decl_name`
- `src/trojanspec/specguard/` — 5 detectors; `axiom_audit.py` is the multi-language post-fix version
- `scripts/02_generate_triples.py` — generation; `04_validate_witnesses.py` — parallel Phase 7 with `--skip-already-validated`
- `scripts/06_phase9_eval.py` + `_phase9_axiom_replay.py` + `_phase9_report.py` — Phase 9 pipeline
- `scripts/10[a-g]_*.py`, `scripts/11_mathlib_case_study.py` — Phase 10 & 11
- `scripts/run_phase*.sh` — orchestrators with per-step `gitci`+push
- `scripts/demo_gradio.py` — Phase 12 Gradio app (atomic-criteria K=2-of-4 over Bedrock Sonnet 4.6); deployed to `m-zest/specguard-demo`
- `scripts/13_hf_dataset_release.py` — Phase 13 dataset builder + uploader; emits parquet + dataset card

## Remaining work (laptop only — no server required)

- **Phase 14** — disclosure email drafts to Cryspen + Symbolic Software referencing the libcrux Hax `SampleNTT` axiom gap (eprint 2026/670) and the libcrux ML-KEM `d ≤ 1` domain restriction (eprint 2026/192). Both anchor real-world implementation_leak / domain_restriction patterns in the benchmark.
- **Phase 15** — paper writing (~4–8 hours). All numbers, figures, methodology, novelty claims, and ablation tables already in `docs/` and `HANDOFF.md`.
