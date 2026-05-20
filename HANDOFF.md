# TrojanSpec-Bench — Final Handoff (v0.2.0)

One-file orientation for picking this project back up on a fresh server.
Everything below — code, data, figures, docs — is in this repo at tag
**`v0.2.0`** (commit `21cb74e` on branch
`claude/professional-search-interface-MCp22`). Two preserved tarballs
(`data/v?_backup_*.tar.gz`) make the run reproducible from a fresh
clone.

---

## 0. Resume on another server — minimal commands

```bash
# 1. Clone + checkout the published state
git clone https://github.com/m-zest/TrojanSpec-Bench-v1.0.git
cd TrojanSpec-Bench-v1.0
git checkout v0.2.0           # or: git checkout claude/professional-search-interface-MCp22

# 2. Credentials (Bedrock — Anthropic Sonnet 4.6 + Haiku 4.5 + Meta Llama-3.3 70B)
cp .env.example .env
$EDITOR .env                  # set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_DEFAULT_REGION

# 3. Single reproduction entry point (idempotent, resumable, banner-printed)
bash scripts/reproduce.sh

# 4. Optional - re-run the Bedrock-billed pipeline (~1-2 h, ~$30 total)
bash scripts/run_phase10_phase11.sh    # 10b, 10c, 10f, 10g, 10h, 10i, 11 (sequential + commit/push)
```

`reproduce.sh` does the cheap stuff (venv, tests, ruff, verifiers, Mathlib
template, dataset restore, Phase 7 verifier re-check, post-hoc Phase 10
ablations) automatically. The Bedrock-billed LLM stages stay opt-in.

See **`docs/REPRODUCIBILITY.md`** for exact env vars, costs, expected
runtimes, and troubleshooting.

---

## 1. What this benchmark is — one paragraph

A **specification-level Trojan** is a formal spec `S` that (i) is accepted
by a verifier when paired with a matching implementation `I` and proof,
(ii) reads to a human as a faithful encoding of the natural-language
requirement `R`, but (iii) does **not** in fact entail `R` — the
verifier proves the wrong theorem. The bug lives in the gap `R \ S`,
which no verifier can see. TrojanSpec-Bench ships 1024 verifier-admitted
trojan triples across **Dafny, Lean 4, and Verus** with paired honest
controls, four attack patterns, real-world cryptographic anchors, the
companion defender **SpecGuard** (5 detectors + a new atomic-criteria
monitor), and 9 ablations under the SpecGuard evaluation. Threat model:
`docs/threat_model.md`.

---

## 2. Taxonomy — the four attack patterns

| Pattern | One-line intuition | Real-world anchor |
|---|---|---|
| **Vacuity** | postcondition is logically `True`, hidden inside a complex expression | Beer et al. 2001 vacuity literature |
| **Implementation leak** | postcondition delegates to an unverified axiom / opaque / `external_body` | libcrux Hax `SampleNTT` axiom gap (eprint 2026/670) |
| **Domain restriction** | precondition silently excludes the dangerous input the NL requires | libcrux ML-KEM decompression (`d ≤ 1` vs `d ∈ {4,5,10,11,12}`, eprint 2026/192) |
| **Predicate swap** | one operator / order / constant flips, English paraphrase still reads correct | Ed25519 pre/post-hash double-clamping |

Per-attack distribution in the admitted set: implementation_leak 377,
vacuity 348, domain_restriction 187, predicate_swap 112.

---

## 3. Previous work / related literature

| Reference | What it gives us |
|---|---|
| **FormalJudge** (arXiv:2602.11136) | atomic decomposition of LLM-as-judge boosts F1 ~16.6% on spec-eval. We replicate this in our setting (Phase 10i). |
| **Epistemic Ensemble** (arXiv:2506.10903) | independent atomic verdicts > coarse omnibus verdicts. Justifies the K-of-4 design. |
| **Terekhov et al.** (adaptive attacker) | inspires Phase 10g — rewrite trojans to evade static markers. |
| **libcrux Hax `SampleNTT` axiom gap** (eprint 2026/670) | real-world `implementation_leak` precedent — an axiom passed crypto review for years. |
| **libcrux ML-KEM decompression bug** (eprint 2026/192) | real-world `domain_restriction` precedent. |
| **Beer et al. 2001** (vacuity detection) | established that vacuous postconditions are a real specification-quality risk. |
| **Mathlib** (Lean 4) | 100-theorem honest sample for `axiom_audit` / `monitor_consensus` FPR calibration (Phase 11). |

---

## 4. Methodology — pipeline summary

```
[NL requirement R]
     │
     │ Bedrock Sonnet 4.6 (Phase 5a, primary)
     │ Bedrock Haiku 4.5 + Llama-3.3 70B (Phase 5b, cross-family)
     ▼
[trojan triple draft: preamble | original_spec | trojan_spec | witness]
     │
     │ Phase 6 review (Sonnet, structural)
     │ Phase 7 admission: real verifier must
     │   accept trojan_spec + witness AND
     │   reject original_spec + witness
     ▼
[1024 admitted trojan triples + 1024 honest controls]
     │
     │ Phase 9 SpecGuard evaluation
     │ Phase 10a–i ablations (this is where the science happens)
     │ Phase 11 Mathlib FPR calibration
     ▼
[paper-ready numbers, figures, and the v0.2.0 release]
```

### 4.1 Generation (Phase 5)
- Elicitor prompt forces the model to produce `original_spec`,
  `trojan_spec`, `preamble`, `witness`, and a `attack_pattern` tag.
- Multi-language: Dafny, Lean 4 + Mathlib, Verus.
- 1500 (Sonnet) + 298 (Haiku/Llama ablation) drafts.

### 4.2 Verifier admission (Phase 7)
- 4 blockers fixed (Lean `lake env lean` instead of `lake build`;
  Dafny `predicate {:axiom}` rather than `function {:axiom}`; preamble
  injection for impl_leak; verifier-proven few-shot rewrites).
- Final admission **57.0% overall** (1024 of 1798); Lean 69.5%, Dafny
  53.2%, Verus 48.2%.

### 4.3 Defender — SpecGuard (Phase 9, 5 detectors over the 1024+1024 set)

| Detector | What it flags | Phase 9 metrics |
|---|---|---|
| `vacuity` | tautological ensures | P 1.000, R 0.056, F1 0.105 |
| `mutation_coverage` | trojan accepts a syntactic mutant of the original | P 1.000, R 0.230, F1 0.373 |
| `ghost_leakage` | postcondition references ghost / spec-only symbol used as a real check | P 1.000, R 0.144, F1 0.253 |
| `axiom_audit` | unverified surface introduced in preamble+trojan_spec not in original_spec (Lean `axiom`/`opaque`, Dafny `{:axiom}`/`{:extern}`, Verus `external_body`/uninterpreted `spec fn`) | **P 0.742, R 0.368, F1 0.492**; R=1.000 on `implementation_leak` |
| `monitor_consensus` | 3 Bedrock monitors (Sonnet+Haiku+Llama) vote FAITHFUL/UNFAITHFUL; majority unfaithful → MALICIOUS | **P 0.771, R 1.000, F1 0.871** |
| **`atomic_monitor`** (Phase 10i) | Sonnet answers **4 atomic Yes/No criteria** (completeness, independence, logical-fidelity, consistency); flag if ≥ 2 fail | **P 0.936, R 1.000, F1 0.967, FPR 0.068** |

`combined_risk` = weighted mean of detector severities; any single
MALICIOUS forces overall MALICIOUS. AUC 0.793, paired Δrisk +0.440.

---

## 5. Results — every phase in one table

| Phase | What it asks | Headline | Doc |
|---|---|---|---|
| 5a / 5b | Can Bedrock Sonnet/Haiku/Llama produce verifier-admitted trojans? | 1500 + 298 drafts | `docs/phase5_to_phase8_complete.md` |
| 7 | What is the verifier admission rate? | **57.0%** (1024/1798); Dafny+Lean 61.3% (≥50% gate cleared) | `data/phase7_admission_report.json` |
| 9 | How well do the 5 SpecGuard detectors discriminate? | `monitor_consensus` **F1 0.871**; `axiom_audit` F1 0.492 (R=1.000 on impl_leak) | `docs/phase9_detector_evaluation.md` |
| 10a | Are trojans from different elicitors equally hard to detect? | Haiku trojans **easier** (`ghost_leakage` R 0.593 vs 0.117 on Sonnet); Llama tracks Sonnet | `docs/phase10_ablations.md` §10a |
| 10b | Is the monitor verdict temperature-sensitive? | **100% temperature-stable** (200/200 UNFAITHFUL at temps 0.0/0.3/0.7/1.0) | §10b |
| 10c | Do 3 or 5 monitors beat 1? | **1 = 3 = 5 in F1** (all 0.900–0.901). Triple cost, no gain. | §10c |
| 10d | Which subset of 5 detectors is F1-optimal? | `monitor_consensus` **alone**; adding `axiom_audit` hurts (shared-preamble FPs → 0.829) | §10d |
| 10e | Does the combined-risk threshold transfer across languages? | Threshold **identical** (0.750) in all 3; per-language F1 spread 0.31 from honest-seed looseness | §10e |
| 10f | How does SSC (single-model, 2-paraphrased-questions) compare? | **Tie**: P=0.771 R=1.000 F1=0.871 FPR=0.297 — same numbers, fewer calls | §10f |
| 10g | What survives an attacker-aware rewrite? | 57/60 (95%) survive re-verification; `axiom_audit` recall **drops 100% → 31.6%**; `mutation_coverage` 28%; the LLM judge remains the principled fallback | §10g |
| 10h | Can SpecGuard *actually* beat SSC (F1 0.871)? | **No on F1.** All 5 hypotheses (static-only Pareto, SSC on Phase 10g adaptive, cross-language stability, LogReg-over-5-features, unanimous-monitor filter) tie SSC. Ceiling is *honest-seed looseness*, not detector quality. SpecGuard wins on cost-Pareto + interpretable evidence. | §10h |
| **10i** | **Does atomic decomposition of the SSC question beat coarse SSC?** | **YES.** Full-set F1 **0.967** (P 0.936, R 1.000, **FPR 0.068**); 5-fold CV F1 **0.967 ± 0.005**, K*=2 on every fold; per-language F1 spread 0.056 (vs SSC 0.31); all 4 attack families ≥ 0.937 at R=1.000. **C3 logical_fidelity alone reaches F1 0.975 at SSC's cost.** | **`docs/phase10i_atomic_monitor.md`** |
| 11 | What's the FPR on real formal mathematics? | 100 honest Mathlib lemmas → `axiom_audit` **0/100**, `monitor_consensus` 23/100 (LLM-judge FPR baseline) | `docs/phase11_mathlib_case_study.md` |
| 12 | Can someone interactively try the detector? | Live Gradio app at **[`m-zest/specguard-demo`](https://huggingface.co/spaces/m-zest/specguard-demo)** running Phase 10i atomic-criteria K=2-of-4 against Bedrock Sonnet 4.6; 3 pre-loaded examples; optional static-detector panel | `scripts/demo_gradio.py`, `hf_space_build/` |
| 13 | Is the dataset publicly available? | **[`m-zest/trojanspec-bench`](https://huggingface.co/datasets/m-zest/trojanspec-bench)** — 1024 admitted triples, parquet, paper-grade dataset card, CC BY 4.0 | `scripts/13_hf_dataset_release.py`, `docs/hf_dataset_card.md` |

---

## 6. What we beat and what we tied

| Comparison | Our number | Baseline | Δ |
|---|---|---|---|
| Atomic K=2-of-4 vs **SSC F1** | 0.967 | 0.871 | **+0.096** |
| Atomic K=2-of-4 vs **SSC FPR** | 0.068 | 0.297 | **−0.229 (4.4× lower)** |
| Atomic C3-alone vs SSC (same cost) | 0.975 | 0.871 | **+0.104** |
| Per-language F1 spread (atomic vs SSC) | 0.056 | 0.31 | **6× tighter** |
| `axiom_audit` post-preamble-fix vs pre-fix | F1 0.492, R 1.000 on impl_leak | F1 0.000 | recovered from 0 |
| Phase 7 admission gate | 57.0% overall, Dafny+Lean 61.3% | ≥50% gate | cleared |
| Phase 10g adaptive `axiom_audit` recall | 31.6% | 100% (Phase 9) | **−68.4 pp** (negative result — static patterns evaded) |

---

## 7. Novelty — what is new in this repo

1. **First multi-language verifier-admitted trojan benchmark** at scale —
   1024 triples across Dafny / Lean 4 / Verus with paired honest
   controls, four attack patterns, and real-world cryptographic anchors.
   v1 dataset preserved alongside v4 so every iteration is replayable.
2. **SpecGuard** — five detectors over `(preamble, original_spec,
   trojan_spec, NL, language)` with multi-language `axiom_audit`
   patterns and a 3-monitor ensemble.
3. **The 0.871 ceiling story (Phase 10h)** — first systematic
   demonstration that the F1 ceiling on this task is set by
   honest-control seed looseness, not by detector quality, under coarse
   `FAITHFUL/UNFAITHFUL` judging.
4. **Atomic-criteria monitor (Phase 10i)** — first replication of the
   FormalJudge / Epistemic Ensemble result in the spec-Trojan setting:
   four independent atomic Yes/No criteria (completeness, independence,
   logical-fidelity, consistency) asked to the same Sonnet judge as SSC,
   combined as K=2-of-4. Lifts F1 from 0.871 → 0.967 (+0.096 absolute)
   and drops FPR from 0.297 → 0.068 (4.4×) with no recall cost. C3 alone
   is the cheapest detector that breaks the ceiling.
5. **Adaptive-attack stress test (Phase 10g)** — quantifies the
   fragility of static detectors: `axiom_audit` recall collapses
   100% → 31.6% on attacker-aware variants; the LLM judge is the
   robustness floor.
6. **Mathlib FPR calibration (Phase 11)** — honest-data baseline on real
   formal mathematics, not synthetic controls.

---

## 8. Honest negative results

- **Phase 9 cross-contamination null** — Llama monitor `miss_rate` on
  Llama-generated trojans is 0.000; no detectable in-family judging bias.
- **Phase 10h H1–H5 all tied SSC** — none of the 5 plausible "beat SSC"
  routes (static-only Pareto, adaptive recall, cross-language stability,
  LogReg over 5 features, unanimous-monitor filter) actually lifted F1.
- **Phase 10g** — the static `axiom_audit` detector is fragile to a
  5-minute attacker-aware rewrite. The semantic LLM judge is what
  survives.
- **Phase 7 Verus** — Verus admission lags Dafny+Lean (48.2% vs 61.3%);
  honest-seed looseness in Verus drives the per-language F1 spread in
  Phase 10e (Dafny 0.995 / Lean 0.851 / Verus 0.677). The Phase 10i
  atomic monitor narrows but does not close this gap (Dafny 0.992 / Lean
  0.970 / **Verus 0.937**).

---

## 9. File layout

```
TrojanSpec-Bench-v1.0/
├── README.md                         # marketing-style overview + headline table
├── STATUS.md                         # full methodology iteration history (v1→v4 + Phase 9 fix)
├── HANDOFF.md                        # ← this file
├── scripts/
│   ├── reproduce.sh                  # single-entrypoint reproducer (idempotent, resumable)
│   ├── install_verifiers.sh          # Dafny 4.11, Lean 4 + Mathlib, Verus, Z3
│   ├── run_phase10_phase11.sh        # opt-in Bedrock-billed batch (10b/c/f/g/h/i + 11)
│   ├── 02_generate_triples.py        # Phase 5 elicitor
│   ├── 03_review_triples.py          # Phase 6 review
│   ├── 04_validate_witnesses.py      # Phase 7 verifier admission
│   ├── 05_specguard.py               # SpecGuard CLI
│   ├── 06_phase9_eval.py             # Phase 9 evaluation
│   ├── 10a_elicitor_sweep.py         # Phase 10a (zero-LLM-cost replay)
│   ├── 10b_monitor_temperature.py    # Phase 10b
│   ├── 10c_monitor_count.py          # Phase 10c
│   ├── 10d_ensemble_grid.py          # Phase 10d (zero-LLM-cost)
│   ├── 10e_cross_language.py         # Phase 10e (zero-LLM-cost)
│   ├── 10f_ssc_baseline.py           # Phase 10f (SSC)
│   ├── 10g_adaptive_attack.py        # Phase 10g (adaptive rewrite)
│   ├── 10h_beat_ssc.py               # Phase 10h (5 hypotheses)
│   ├── 10i_atomic_monitor.py         # ← Phase 10i (the win)
│   ├── 11_mathlib_case_study.py      # Phase 11
│   └── _phase*_report.py             # post-hoc reporters
├── src/trojanspec/                   # importable library (schemas, verifiers, detectors)
├── tests/                            # pytest 58 passed / 3 skipped
├── data/
│   ├── triples/, triples_xfamily/    # admitted v4 triples (restored from tarball)
│   ├── triples_v1/, triples_xfamily_v1/  # v1 negative-result corpus (preserved)
│   ├── v1_backup_*.tar.gz            # source-of-truth tarballs (do not delete)
│   ├── v4_backup_*.tar.gz
│   ├── phase7_admission_report.json  # Phase 7
│   ├── phase9_results_v2.jsonl       # Phase 9 (post-fix v2)
│   ├── phase9_metrics_v2.json
│   ├── phase10_10a..10i_*.json{,l}   # Phase 10 ablations
│   ├── phase10_10i_atomic.json       # ← Phase 10i summary
│   ├── phase10_10i_atomic_results.jsonl   # ← Phase 10i per-triple verdicts
│   └── phase11_results.jsonl + summary.json
├── figures/
│   ├── phase9_*.png
│   ├── phase10_*.png
│   └── phase10_atomic_vs_ssc.png     # ← Phase 10i headline figure
└── docs/
    ├── REPRODUCIBILITY.md            # env vars, costs, runtimes, troubleshooting
    ├── threat_model.md
    ├── schema.md
    ├── data_card.md
    ├── disclosure_policy.md
    ├── phase5_to_phase8_complete.md
    ├── phase9_detector_evaluation.md
    ├── phase10_ablations.md          # all 10 ablations including the new 10i
    ├── phase10i_atomic_monitor.md    # ← Phase 10i deep dive
    └── phase11_mathlib_case_study.md
```

---

## 10. Reproduction recipes (specific re-runs without re-doing everything)

```bash
# Just regenerate Phase 10i numbers + figure from the committed JSONL
./venv/bin/python scripts/10i_atomic_monitor.py --analyze-only

# Re-run Phase 10i end-to-end (8192 Sonnet calls, ~$4)
./venv/bin/python scripts/10i_atomic_monitor.py --concurrency 12

# Re-run SSC baseline (Phase 10f)
./venv/bin/python scripts/10f_ssc_baseline.py

# Re-run the 5 hypotheses against SSC (Phase 10h)
./venv/bin/python scripts/10h_beat_ssc.py

# Adaptive attacker rewrite (Phase 10g; 60 impl_leak triples)
./venv/bin/python scripts/10g_adaptive_attack.py --sample 60

# Mathlib case study (Phase 11; 100 theorems)
./venv/bin/python scripts/11_mathlib_case_study.py --target 100

# Verifier admission re-check (Phase 7; offline, no LLM cost)
./venv/bin/python scripts/04_validate_witnesses.py \
  --data-dir data/triples data/triples_xfamily --skip-already-validated

# Zero-LLM-cost post-hoc Phase 10 ablations (always safe to re-run)
./venv/bin/python scripts/10a_elicitor_sweep.py
./venv/bin/python scripts/10d_ensemble_grid.py
./venv/bin/python scripts/10e_cross_language.py
```

All LLM-heavy scripts stream to JSONL and are **resumable** — re-running
continues where the JSONL left off; `--analyze-only` on the same script
regenerates JSON + figure from the existing JSONL.

---

## 11. Pre-flight checklist on a fresh server

```bash
# After `bash scripts/reproduce.sh` completes, verify:
[ -f data/phase7_admission_report.json ]          && echo OK phase7
[ -f data/phase9_results_v2.jsonl ]               && echo OK phase9
[ -f data/phase9_metrics_v2.json ]                && echo OK phase9-metrics
[ -f data/phase10_10i_atomic.json ]               && echo OK phase10i
[ -f figures/phase10_atomic_vs_ssc.png ]          && echo OK phase10i-figure
./venv/bin/python -c "
import json
m = json.load(open('data/phase10_10i_atomic.json'))
assert abs(m['best_rule_full']['f1'] - 0.967) < 1e-3
assert m['cv_rule_k']['mean_test_f1'] >= 0.96
print('phase 10i numbers match release: F1 =', m['best_rule_full']['f1'])
"
```

If any of these fail on the fresh server, the most likely cause is a
Bedrock credential issue — see `docs/REPRODUCIBILITY.md` §troubleshooting.

---

## 12. What is intentionally NOT in this repo

- Bedrock credentials (`.env` is gitignored; user must populate).
- The Lean+Mathlib snapshot itself (rebuilt locally by `reproduce.sh`
  step 4, ~20–40 min on first run).
- The 334 stray Verus binaries that briefly leaked into commit `bdf082f`
  — untracked in `744ddad`; `tmp*` added to `.gitignore`; `verus.py` now
  uses a per-call `tempfile.mkdtemp` cleaned in `finally` so the leak
  cannot recur.

---

## 13. Cost / runtime summary for a fresh full re-run

| Stage | LLM calls | $ | Wall clock |
|---|---:|---:|---:|
| Phase 5a/5b generation (already in tarballs) | – | – | 0 (restored) |
| Phase 7 verifier admission re-check | 0 | 0 | ~1 h (parallel) |
| Phase 9 SpecGuard eval (already committed v2) | 0 | 0 | 0 (cached) |
| Phase 10a/d/e (post-hoc) | 0 | 0 | ~30 s |
| Phase 10b temperature | ~800 | ~$0.40 | ~5 min |
| Phase 10c monitor count | ~3000 | ~$1.50 | ~10 min |
| Phase 10f SSC baseline | ~8200 | ~$4 | ~45 min |
| Phase 10g adaptive | ~600 | ~$0.30 | ~5 min |
| Phase 10h beat-SSC (H2 SSC on 57 adaptive) | ~230 | ~$0.10 | ~5 min |
| **Phase 10i atomic monitor** | **~8200** | **~$4** | **~30 min** |
| Phase 11 Mathlib | ~600 | ~$0.30 | ~10 min |
| **Total opt-in Bedrock budget** | **~22000** | **~$11** | **~2 h** |

(Estimates from this run; concurrency=12 on Bedrock cross-region
inference profiles.)

---

## 14. The single sentence

> Decomposing the coarse `FAITHFUL / UNFAITHFUL` LLM-judge question into
> four independent atomic Yes/No criteria and flagging when ≥ 2 fail
> lifts F1 from 0.871 → 0.967 and drops FPR from 0.297 → 0.068 on the
> 1024-trojan TrojanSpec-Bench evaluation, validating the FormalJudge /
> Epistemic Ensemble decomposition principle in the spec-Trojan setting
> at no recall cost.

Tag: **`v0.2.0`** · Commit: **`21cb74e`** · Branch:
`claude/professional-search-interface-MCp22` · Origin:
`https://github.com/m-zest/TrojanSpec-Bench-v1.0`.
