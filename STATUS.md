# TrojanSpec-Bench: Status and Handoff

**Updated:** 2026-05-24
**Branch:** `main` (tag `v0.4.2`)
**Reproduce:** `bash scripts/reproduce.sh` (idempotent; reads
[`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) for environment variables).

---

## TL;DR

The library, generators, three verifier wrappers, 13 crypto-primitive
anchors, **SpecGuard (six detectors)**, the Bedrock generation pipeline
(Phase 5a/5b), the parallel verifier (Phase 7), the SpecGuard evaluation
(Phase 9), the seven ablations (Phase 10a through 10i), the Mathlib case
study (Phase 11), the **Phase 12 Gradio demo on HF Spaces**, the
**Phase 13 HF dataset release**, and the **Phase 14 MutDafny
head-to-head** are all built, tested, and committed. The v0.4.1
hackathon paper is published in `paper/` with a 9-page PDF and a
20-row cross-reference audit (`PAPER_AUDIT.md`). `pytest` runs 58
passed / 3 skipped, `ruff` is clean.

The benchmark is shippable from a fresh clone via two preserved tarballs
(`data/v1_backup_*.tar.gz`, `data/v4_backup_*.tar.gz`) and
`reproduce.sh`. Public artifacts:

- HuggingFace Dataset: https://huggingface.co/datasets/m-zest/trojanspec-bench
- HuggingFace Demo: https://huggingface.co/spaces/m-zest/specguard-demo

---

## Headline numbers

| Phase | Headline |
| :-- | :-- |
| **5a / 5b** Generation | 1,500 admitted (Sonnet 4.6) + 298 ablation (Haiku 4.5 + Llama-3.3 70B) |
| **7** Admission | **57.0%** overall (1,024 / 1,798); Dafny + Lean 61.3% (gate >= 50% cleared); Lean 69.5%, Dafny 53.2%, Verus 48.2% |
| **9** SpecGuard | `monitor_consensus` **F1 0.871** (R 1.000, P 0.771, FPR 0.297); `axiom_audit` **F1 0.492** post multi-language + preamble fix (R 1.000 on `implementation_leak`); combined-risk AUC 0.793, paired delta-risk +0.440 |
| **10** Ablations | a (elicitor sweep), b (temperature), c (monitor count 1/3/5), d (ensemble grid: `monitor_consensus` alone is F1-optimal), e (cross-language transfer: threshold transfers perfectly), f (SSC baseline), g (adaptive-attack stress), h (5 hypotheses against SSC, all TIE), **i (atomic-criteria K = 2 of 4: F1 0.967, +0.096 over SSC, FPR 0.297 -> 0.068)** |
| **11** Mathlib | 100 honest Lean theorems through `axiom_audit` + `monitor_consensus` + `atomic_monitor` (real-formal-mathematics FPR calibration: 0 / 100, 23 / 100, **3 / 100**) |
| **14** MutDafny head-to-head | On 319 admitted Dafny trojans: our `mutation_coverage` F1 0.540 vs MutDafny F1 0.530 (tie, McNemar p = 0.895); atomic_monitor K=2 F1 **0.992** strictly dominates MutDafny (McNemar p < 10^-45, strict superset) |

---

## Methodology story (the iteration history that became the paper)

### v1 -> v3 contract iterations (Phase 5-redux)

| Ver | Contract | Bug it exposed via automated validation | Admission |
| :-- | :-- | :-- | :-- |
| **v1** | trojan_spec + trojan_witness each a full standalone program | concatenation duplicate-declares the symbol; never compiles | 0.13 % (1/756) |
| **v2** | single signature; spec = header only, witness = body | `compose()` brace-finding broke on set literals / `{:axiom}` / `verus!`; Lean `original_spec` was a *different declaration* than the trojan | 10 % (1/10) |
| **v3** | shared **preamble** (helpers) + single target spec/witness | preamble fixed all `schema_mismatch`; 0/20 source-audit drops | 10 % (1/10) |

### v4: the four blockers that lifted admission to 57%

Each gate exposed one structural bug; fixing each lifted real admission:

1. **FIX 5 (Lean verifier real type-checking).** `verify_lean` ran
   `lake build`, which builds the project's `defaultTargets` and returns
   exit code 0 *without* type-checking the injected `Main.lean`. Every
   Lean triple spuriously "verified" and the honest original was never
   rejected. Switched to `lake env lean Main.lean`. Commit `284cec3`.
2. **Verifier-proven Lean few-shot.** Rewrote all 8 Lean worked examples
   (A+B x 4 attacks) onto four shapes confirmed `acc_troj=True
   rej_orig=True` through the fixed `verify_lean`. Commit `284cec3`.
3. **`implementation_leak` Dafny few-shot was structurally wrong.**
   `function {:axiom} P(...): bool` + `ensures P(...)` does not verify
   (Dafny still tries to prove the ensures; `{:axiom}` on a bodyless
   function does not axiomatize claims about its value). Replaced with
   `predicate {:axiom}` + `lemma {:axiom}` that the witness invokes.
   Commit `e6b6111`.
4. **Deterministic Lean `implementation_leak` repair in the elicitor.**
   Sonnet reliably named a leak surface in `trojan_spec` / `witness` but
   omitted its declaration from `preamble`, so the trojan never
   type-checked. Added `_repair_lean_impl_leak` in
   `src/trojanspec/generators/elicitor.py`: synthesises a nullary opaque
   `Prop` plus inhabiting axiom in the preamble from the original
   theorem header (no type inference; only a depth-0 goal-colon split).
   Removes model-compliance dependence. Commit `3a13228`.

Sanity progression: **10% -> 50% -> 50% -> 60%** as each blocker closed.
Full 1500 + 300 regeneration plus Phase 7 then landed at **57.0%**
overall (`bdf082f` Phase 7 report; `d9d40ea` final progression report).

### Phase 9 SpecGuard evaluation

Five static and LLM-based detectors x 1,024 admitted trojan triples plus
1,024 honest controls. Initial run reported `axiom_audit` at 0/1024.
Diagnosed as compounding bugs (Lean-only language scope; `trojan_spec`-
only inspection scope misses the preamble-located v4 deterministic leak
repair). Rewrote the detector with per-language patterns (Lean
`axiom`/`opaque`, Dafny `{:axiom}`/`{:extern}`, Verus
`external_body`/uninterpreted `spec fn`) over `preamble + trojan_spec`.
Replay over the existing jsonl (no LLM re-cost) lifted 0 -> 377 true
positives (100% recall on `implementation_leak`). Commit `af67337`.

The atomic-criteria detector (`atomic_monitor`) was added as the sixth
detector in Phase 10i; see Phase 10 + 11 + 14 below.

Honest-control caveat: the seed `original_spec` is often loose vs the
NL (e.g. NL "sum 0..n" paired with a spec that only `ensures r >= n`),
so the unpaired FPR on `monitor_consensus` (0.297) is conservative-high.
The paired delta-rate (70.3%) is the discriminative measure that
controls for seed quality.

### Phase 10 + 11 + 14 (complete)

Full results in `docs/phase10_ablations.md`,
`docs/phase11_mathlib_case_study.md`, and `docs/mutdafny_comparison.md`.

- **10a (elicitor sweep).** Haiku-generated trojans are markedly easier
  to detect (`ghost_leakage` R 0.593 vs 0.117 on Sonnet, `axiom_audit`
  R 0.508 vs 0.353). Llama tracks Sonnet.
- **10b (temperature).** Sonnet verdict is 100% temperature-stable on
  admitted trojans (200/200 UNFAITHFUL at temps 0.0/0.3/0.7/1.0).
- **10c (monitor count).** **1 monitor = 3 monitors = 5 monitors** in
  F1 (all 0.900 to 0.901). Single Sonnet is as accurate as the
  3-monitor consensus; adding monitors changes precision by 0.003.
  **3x cost reduction with no quality loss.**
- **10d (ensemble grid).** `monitor_consensus` alone is the F1-optimal
  subset (0.871); adding `axiom_audit` *hurts* F1 to 0.829
  (shared-preamble FPs).
- **10e (cross-language).** Combined-risk threshold transfers perfectly
  (0.750 in all three languages); per-language F1 varies (Dafny 0.995 /
  Lean 0.851 / Verus 0.677) by honest-control seed looseness.
- **10f (SSC baseline).** Single-model two-paraphrased-question
  consistency check is **identical to monitor_consensus**: P=0.771
  R=1.000 F1=0.871 FPR=0.297. Pareto-equivalent at 2 calls vs 3.
- **10g (adaptive attack, Terekhov-style).** Sonnet rewrote 60 admitted
  impl_leak trojans without axiom-like markers; 57/60 (95%) survived
  re-verification. `axiom_audit` recall on the adaptive set
  **drops 100% -> 31.6%**. `mutation_coverage` held up best (28% catch
  on adaptive). The semantic LLM judge remains the principled fallback
  when static patterns are evaded.
- **10h (can SpecGuard beat SSC?).** Five hypotheses tested (static-only
  Pareto, SSC on Phase 10g adaptive, cross-language stability,
  LogReg-over-5-detectors, unanimous-monitor filter). All tied SSC at
  F1 0.871. The 0.871 ceiling was honest-control seed looseness, not
  detector quality, under coarse `FAITHFUL/UNFAITHFUL` framing.
- **10i (atomic-criteria monitor: the actual win).** Decomposing the
  coarse SSC question into four independent atomic Yes/No criteria
  (completeness, independence, logical-fidelity, consistency) and
  flagging when at least two fail breaks the 0.871 ceiling. Full-set
  **F1 0.967** (P 0.936, R 1.000, **FPR 0.068**); 5-fold CV F1
  **0.967 +/- 0.005** with K* = 2 on every fold. Per-language F1 spread
  shrinks from 0.31 (SSC) to 0.056 (Dafny 0.992 / Lean 0.970 / Verus
  0.937); all four attack families clear F1 >= 0.937 at 100% recall.
  The C3-alone (logical-fidelity) variant is the cheapest detector that
  beats SSC (F1 **0.975** at 2 calls/side, same cost as SSC). Validates
  the FormalJudge / Epistemic Ensemble finding in the spec-Trojan
  setting. Cost: 8,192 Sonnet calls, 0 malformed.
- **11 (Mathlib calibration).** 100 honest Mathlib lemmas through three
  detectors: `axiom_audit` flags 0/100 (the post-fix pattern set is
  selective; no real Mathlib lemma in the sample introduces a new
  axiom), `monitor_consensus` 23/100 (LLM-judge FPR baseline on real
  formal mathematics), **atomic_monitor 3/100** (strict subset of the
  consensus flags; 7.7x reduction at the same recall).
- **12 (HF Space demo).** Interactive Gradio app at
  https://huggingface.co/spaces/m-zest/specguard-demo runs the Phase
  10i atomic-criteria detector against Bedrock Sonnet 4.6 with three
  pre-loaded examples and an optional static-detector panel. Source:
  `scripts/demo_gradio.py`, deployed bundle in `hf_space_build/`.
- **13 (HF Dataset release).** 1,024 admitted triples published at
  https://huggingface.co/datasets/m-zest/trojanspec-bench as a single
  parquet `test` split. Paper-grade dataset card with schema, threat
  model, per-language admission, per-attack distribution,
  elicitor-origin counts, detector evaluation summary (Phase 9 + 10i),
  CC BY 4.0 license, BibTeX citation. Verified
  `load_dataset("m-zest/trojanspec-bench")` works publicly. Builder:
  `scripts/13_hf_dataset_release.py`; card mirrored to
  `docs/hf_dataset_card.md`.
- **14 (MutDafny head-to-head).** On the 319 admitted Dafny trojans,
  our `mutation_coverage` F1 0.540 vs the published ICSE 2026 MutDafny
  tool (Amaral, Mendes, Campos. arXiv:2511.15403) F1 0.530 (tie,
  McNemar p = 0.895). atomic_monitor K=2 F1 **0.992** is a strict
  superset of MutDafny on the trojan side (McNemar p < 10^-45). Per
  attack: ours catches `implementation_leak` (99.2% on Dafny), MutDafny
  catches `vacuity` (98.3%), neither catches `domain_restriction` or
  `predicate_swap`. Mutation-based detection has a structural ceiling:
  it is essentially a vacuity detector on this benchmark.
- **Phase 9 cross-contamination null result.** Llama-monitor `miss_rate`
  on Llama-generated trojans = 0.000; no detectable in-family judging
  bias.

---

## What is preserved for clone-and-resume

| Artefact | Location | Restored to |
| :-- | :-- | :-- |
| v1 dataset (1,484 + 212 negative-result corpus) | `data/v1_backup_*.tar.gz` | `data/triples_v1/`, `data/triples_xfamily_v1/` |
| v4 dataset (1,500 + 298 admitted triples) | `data/v4_backup_*.tar.gz` | `data/triples/`, `data/triples_xfamily/` |
| Phase 7 report | `data/phase7_admission_report.json` | (committed) |
| Phase 9 results + metrics | `data/phase9_results_v2.jsonl`, `data/phase9_metrics_v2.json` | (committed) |
| Phase 9 figures | `figures/phase9_*.png` | (committed via `!figures/phase9_*.png` exception) |
| Phase 10 + 11 data + figures | `data/phase10_*`, `data/phase11_*`, `figures/phase10_*.png` | (committed; `!figures/phase10_*.png` exception in `.gitignore`) |
| Phase 12 demo source + HF Space bundle | `scripts/demo_gradio.py`, `hf_space_build/` | (committed; Space live at `m-zest/specguard-demo`) |
| Phase 13 dataset builder + card | `scripts/13_hf_dataset_release.py`, `docs/hf_dataset_card.md` | (committed; dataset live at `m-zest/trojanspec-bench`) |
| Phase 14 MutDafny comparison | `data/phase14_*`, `scripts/14_*`, `scripts/run_phase14.sh`, `scripts/install_mutdafny.sh`, `docs/mutdafny_comparison.md` | (committed) |
| Paper source (LaTeX + Makefile + PDF) | `paper/trojan_bench.tex`, `paper/Makefile`, `paper/trojan_bench.pdf` | (committed) |
| Paper audit cross-reference | `PAPER_AUDIT.md` | (committed at repo root) |
| Lean + Mathlib template | `$HOME/lean-project-template` | rebuilt by `reproduce.sh` step 4 (one-time ~20 to 40 min) |

---

## What is NOT in this repo

- Bedrock credentials (must be put in `.env` by the user).
- The Lean + Mathlib snapshot itself (rebuilt locally by `reproduce.sh`).
- The 334 stray Verus binaries that briefly leaked into commit `bdf082f`
  (untracked in `744ddad`, `tmp*` added to `.gitignore`, and `verus.py`
  now uses a per-call `tempfile.mkdtemp` cleaned in `finally` so the
  leak cannot recur). History still contains the blobs in `bdf082f`;
  history rewrite is a separate, destructive call.

---

## Key files

- `src/trojanspec/schemas.py`: `Triple` (`preamble`, `validation_failed`,
  `schema_mismatch`, `is_admitted`).
- `src/trojanspec/verifiers/{dafny,lean,verus}.py`: verifier wrappers
  (FIX 5, main-injection, tmpdir cleanup).
- `src/trojanspec/verifiers/compose.py`:
  `compose(preamble, contract, witness, lang)`.
- `src/trojanspec/generators/elicitor.py`: `_repair_lean_impl_leak`
  (deterministic leak surface in preamble).
- `src/trojanspec/generators/validator.py`: Phase 7 verifier driver;
  `_target_decl_name`.
- `src/trojanspec/specguard/`: **six detectors**, with
  `atomic_monitor.py` promoted to library module and `axiom_audit.py`
  in its multi-language post-fix form.
- `scripts/02_generate_triples.py`: generation;
  `04_validate_witnesses.py`: parallel Phase 7 with
  `--skip-already-validated`.
- `scripts/06_phase9_eval.py` + `_phase9_axiom_replay.py` +
  `_phase9_report.py`: Phase 9 pipeline.
- `scripts/10[a-i]_*.py`, `scripts/11_mathlib_case_study.py`: Phase 10
  and Phase 11.
- `scripts/14_*.py`, `scripts/run_phase14.sh`: Phase 14 MutDafny
  head-to-head.
- `scripts/run_phase*.sh`: orchestrators with per-step commit and push.
- `scripts/demo_gradio.py`: Phase 12 Gradio app (atomic-criteria
  K=2-of-4 over Bedrock Sonnet 4.6); deployed to `m-zest/specguard-demo`.
- `scripts/13_hf_dataset_release.py`: Phase 13 dataset builder and
  uploader; emits parquet + dataset card.
- `paper/trojan_bench.tex`: LaTeX source for the v0.4.1 Apart Research
  hackathon paper. `paper/Makefile` builds the PDF.
- `PAPER_AUDIT.md`: cross-reference of every paper claim to its source
  JSON file (20 corrections logged versus the v0.4.0 paper draft).

---

## Completed since v0.4.0

- **Phase 14 (MutDafny head-to-head).** On the 319 admitted Dafny
  trojans, atomic_monitor K=2 reaches F1 0.992 vs the published ICSE
  2026 MutDafny baseline at F1 0.530 (McNemar p < 10^-45, strict
  superset). Static mutation testing detects vacuity but is structurally
  blind to the other three attack classes. Reproducible in ~75 min at
  $0 Bedrock cost via `scripts/run_phase14.sh`. See
  `docs/mutdafny_comparison.md`.
- **Paper (Apart Research SPS Hackathon, May 2026).** Nine-page paper
  submitted with 20 corrections sourced to JSON data files; see
  `PAPER_AUDIT.md`. LaTeX source in `paper/trojan_bench.tex`, build with
  `cd paper && make paper`.
- **README polish (v0.4.2).** Cleaner structure, table of contents,
  six-detector comparison table, deployment rationale for atomic K=2
  over C3 alone.
- **Documentation consistency pass (v0.4.2).** McNemar p-value corrected
  to p < 10^-45 across CHANGELOG, STATUS, and HANDOFF (precise value
  2.8 x 10^-46 derived from chi-squared = 204 on 1 d.f.). Detector count
  unified at six. Phase 14 status updated everywhere.

---

## Open / future work

- **Cross-vendor attacker-judge partition.** Sonnet generates the
  trojans while Haiku judges (and vice versa). Highest-priority
  follow-up because the same model currently sits on both sides of the
  test.
- **Atomic detector under adaptive attack.** Analogous to Phase 10g
  (which targeted `axiom_audit`) but with an attacker that knows the
  four atomic criteria and tries to evade two of them simultaneously.
  The atomic monitor was not stress-tested this way in v0.4.x.
- **Mathlib scale-up.** Currently 100 lemmas with Wilson 95% CI of 1.0%
  to 8.5% on the atomic FPR. A 1,000-lemma evaluation would tighten the
  CI.
- **Deployment integration.** `atomic_monitor` as a pre-commit hook in
  a real Dafny project, to surface deployment failure modes that the
  benchmark cannot model.

The "Phase 14 disclosure emails" item that appeared in earlier
versions of this file was superseded by the MutDafny head-to-head, which
proved to be the more rigorous comparison. Disclosure emails to Cryspen
and Symbolic Software remain possible but are no longer on the critical
path.
