# TrojanSpec-Bench — Reproducibility Guide

Step-by-step instructions to bring up a fresh machine and re-run the
benchmark, the SpecGuard evaluation (Phase 9), the ablations (Phase 10), and
the Mathlib case study (Phase 11). The companion script
[`scripts/reproduce.sh`](../scripts/reproduce.sh) automates the idempotent
parts; this document is the spec.

---

## 1. Prerequisites

| Component | Version | Why |
| :-- | :-- | :-- |
| OS | Linux x86_64 (tested on Ubuntu 22.04, kernel 6.8) | Verus / Dafny / Lean 4 binaries |
| Python | ≥ 3.10 | Pydantic 2 / asyncio / type-union syntax |
| Disk | ≥ 60 GB free | Mathlib (~12 GB cache + build), pip cache, repo, scratch |
| RAM | ≥ 16 GB | Lean type-check; 32 GB+ recommended for parallel Phase 7 |
| CPU | ≥ 8 cores | parallel Phase 7 verification (4-way `ProcessPoolExecutor`) |
| Network | yes | AWS Bedrock; HF model registry; Lean/Mathlib cache |

## 2. AWS Bedrock credentials

The generator (Phase 5a/5b) and the SpecGuard monitor (Phase 9 / 10b–f)
both call **AWS Bedrock**. Three Bedrock model families are used as
cross-region inference profiles:

| Family alias | Bedrock model id |
| :-- | :-- |
| `bedrock-claude-sonnet` | `us.anthropic.claude-sonnet-4-6` |
| `bedrock-claude-haiku` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` |
| `bedrock-llama-70b` | `us.meta.llama3-3-70b-instruct-v1:0` |

Set in `.env` (copy from `.env.example`):

```bash
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
```

The IAM role needs `bedrock:InvokeModel` on the three model ids above.
Bedrock throttling backoff is built-in (`_THROTTLE_BASE_DELAY = 8 s`, up to
5 retries) — sustained throttling for ~30 min is a hard stop in the
orchestrators.

## 3. Verifiers

Run [`scripts/install_verifiers.sh`](../scripts/install_verifiers.sh) (called
from `reproduce.sh`). It installs:

| Verifier | Source |
| :-- | :-- |
| **Z3 4.8.12** | `pip install z3-solver` (transitive) |
| **Dafny 4.11** | `dotnet tool install --global Dafny` |
| **Lean 4.29 + Mathlib** | `elan` toolchain manager + `lake new ... math` + `lake exe cache get` (~20–40 min first build) |
| **Verus** | `cargo install --git https://github.com/verus-lang/verus` (or build from source; historically the failure case is missing Z3 binary — Verus expects `z3` on `PATH`) |

After install, `verify_lean` / `verify_dafny` / `verify_verus` in
[`src/trojanspec/verifiers/`](../src/trojanspec/verifiers/) wrap the
binaries. `verify_lean` requires `TROJANSPEC_LEAN_TEMPLATE` pointing at a
Lean project with Mathlib pre-built — `reproduce.sh` step 4 sets this up
once and marks `$TPL/.mathlib_ready` so re-runs skip the slow build.

## 4. Restoring preserved datasets

Two tarballs ship in `data/` (kept via the `!data/v?_backup_*.tar.gz`
exception to the broad `data/*.tar.gz` ignore):

| Tarball | Contents | Restored to |
| :-- | :-- | :-- |
| `data/v1_backup_*.tar.gz` | 1484 + 212 v1 triples (early-iteration negative result; structurally broken concatenation contract — methodology evidence) | `data/triples_v1/`, `data/triples_xfamily_v1/` |
| `data/v4_backup_*.tar.gz` | 1500 + 298 admitted v4 triples (headline benchmark, Phase 5a + 5b) | `data/triples/`, `data/triples_xfamily/` |

`reproduce.sh` step 2 restores both. The raw triple JSONs themselves are
gitignored to keep the working tree clean; the tarballs are the canonical
source of truth.

## 5. Phase-by-phase index

A complete rebuild *from scratch* (no tarballs) would call Phase 5a/5b
generation through Phase 11 in order. Most users only need to **restore**
the tarballs and re-run **Phase 7 onwards** (no Bedrock cost for steps that
operate on stored verifier verdicts).

| Phase | Script(s) | Inputs | Outputs | Cost |
| :-: | :-- | :-- | :-- | :-- |
| 5a | `scripts/02_generate_triples.py` | crypto anchors, NL seeds | `data/triples/**/*.json` (1500) | Bedrock Sonnet |
| 5b | `scripts/02_generate_triples.py --xfamily` | anchors | `data/triples_xfamily/**/*.json` (300) | Bedrock Haiku + Llama |
| 7 | `scripts/04_validate_witnesses.py --concurrency 4 --skip-already-validated` | both data dirs | `data/phase7_admission_report.json` + stamped JSONs | verifier-only (no LLM) |
| 9 | `scripts/06_phase9_eval.py` + `scripts/_phase9_axiom_replay.py` + `scripts/_phase9_report.py` | admitted triples | `data/phase9_results_v2.jsonl`, `data/phase9_metrics_v2.json`, `docs/phase9_detector_evaluation.md`, `figures/phase9_*.png` | Bedrock × 3 monitors × 1024 trojan + 1024 honest |
| 10a | `scripts/10a_elicitor_sweep.py` | phase9 jsonl | `data/phase10_10a_*.json`, figure | **zero LLM** |
| 10b | `scripts/10b_monitor_temperature.py --sample 200` | admitted triples | `data/phase10_10b_*.json` | Bedrock Sonnet × 4 temps × 200 |
| 10c | `scripts/10c_monitor_count.py --sample 300` | admitted triples | `data/phase10_10c_*.json` | Bedrock × {1,3,5} × 300 |
| 10d | `scripts/10d_ensemble_grid.py` | phase9 jsonl | `data/phase10_10d_*.json`, figure | **zero LLM** |
| 10e | `scripts/10e_cross_language.py` | phase9 jsonl | `data/phase10_10e_*.json`, figure | **zero LLM** |
| 10f | `scripts/10f_ssc_baseline.py` | admitted triples | `data/phase10_10f_ssc_*` | Bedrock Sonnet × 4 calls × 1024 |
| 10g | `scripts/10g_adaptive_attack.py --sample 60` | admitted impl_leak triples | `data/phase10_10g_*` | Bedrock Sonnet × 60 + verifier |
| 11 | `scripts/11_mathlib_case_study.py --target 100` | Mathlib snapshot | `data/phase11_*` | Bedrock × 3 monitors × 100 |

Orchestrators:

- `scripts/run_phaseA4_parallel.sh` — Phase 7 (parallel resume, gate ≥50%, final report)
- `scripts/run_phase9.sh` — Phase 9 eval (1024+1024, ProcessPool of monitors)
- `scripts/run_phase10_phase11.sh` — sequential 10b → 10c → 10f → 10g → 11

Each orchestrator commits + pushes per stage with the project identity
`Mohammad Zeeshan <hdglit@inf.elte.hu>`. Logs `/tmp/phase*.log`. Terminal
markers `PHASE_*_SUCCESS` / `PHASE_*_STOPPED`.

## 6. Cost estimates (Bedrock, approximate)

| Stage | LLM calls | Approx token cost |
| :-- | --: | --: |
| Phase 5a generation (1500) | ~3000 | ~$15 (Sonnet) |
| Phase 5b ablation (300) | ~600 | ~$2 (Haiku + Llama) |
| Phase 9 monitor consensus | 1024 × 3 monitors × 2 sides = 6144 | ~$15 |
| Phase 10b temperature | 200 × 4 = 800 | ~$2 |
| Phase 10c count {1,3,5} | 300 × ~5 (cached) = 1500 | ~$3 |
| Phase 10f SSC | 1024 × 4 = 4096 | ~$10 |
| Phase 10g adaptive | 60 + 60 verifier calls | ~$1 |
| Phase 11 Mathlib | 100 × 3 = 300 | ~$1 |
| **Total full rebuild** | | **~$50** |

A reproduction that **does not re-generate** Phase 5 (i.e. uses the
restored v4 tarball) cuts ~$17 off the top. Phase 9 alone is ~$15. The
post-hoc-only path (steps 5–7 of `reproduce.sh`) costs $0.

## 7. Runtime estimates (wall clock)

| Stage | Wall time |
| :-- | --: |
| First-time Mathlib build | 20–40 min |
| Phase 5a (1500 generations, Bedrock concurrency 4) | ~2 h |
| Phase 5b (300 generations) | ~30 min |
| Phase 7 verification (1798 triples, parallel ×4) | ~3 h |
| Phase 9 evaluation (concurrency 4) | ~35 min (measured) |
| Phase 10 LLM ablations + Phase 11 | ~1–2 h |

The orchestrators are resumable: re-running picks up where it stopped.

## 8. Key environment variables

| Var | Where | Purpose |
| :-- | :-- | :-- |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_DEFAULT_REGION` | `.env` | Bedrock auth |
| `TROJANSPEC_LEAN_TEMPLATE` | shell / orchestrators | Path to Lean+Mathlib project (`verify_lean` copies it per call) |
| `PATH` | shell | Must include `$HOME/.dotnet/tools` (Dafny) and `$HOME/.elan/bin` (Lean) |

## 9. Troubleshooting

- **Verus emits `tmp*` binaries into cwd.** Fixed in `src/trojanspec/verifiers/verus.py` (per-call `tempfile.mkdtemp()` + `shutil.rmtree` in `finally`). Pre-fix runs left ~334 binaries in the repo root; `.gitignore` now has `tmp*` to prevent re-commit.
- **`lake build` returns 0 without type-checking.** Lean ≥ 4.29 quirk; we run `lake env lean Main.lean` instead. See `src/trojanspec/verifiers/lean.py` FIX 5 history.
- **`verify_verus` errors with `E0601 main`.** Composed triples have no `main`; the wrapper injects a trivial `fn main() {}` when absent.
- **Bedrock `ThrottlingException`.** Account-level rate limit; the client backs off 8 s, 16 s, 32 s, 64 s, 128 s (5 retries). Sustained throttling stops the orchestrator with `PHASE_*_STOPPED`.
- **Honest-control FPR looks high (~30%) on `monitor_consensus`.** Documented in `docs/phase9_detector_evaluation.md`: the original_spec is the *crypto-anchor seed* (often loose vs the NL), not a gold-standard formal reference. Use the paired-Δ column for discriminative measurement.
- **`axiom_audit` flagged 0 triples in initial Phase 9.** Fixed: was Lean-only + `trojan_spec`-only; now multi-language + `preamble + trojan_spec`. Re-evaluation in commit `af67337`. See the Phase 9 follow-up section of `docs/phase9_detector_evaluation.md`.

## 10. Reproducibility checklist (for the paper)

- [ ] Same git commit (record SHA at submission)
- [ ] Same dataset tarballs (`v1_backup_*.tar.gz`, `v4_backup_*.tar.gz` in `data/`)
- [ ] Same Bedrock model versions (`us.anthropic.claude-sonnet-4-6`, etc.)
- [ ] Same verifier versions (Dafny 4.11, Lean 4.29 + Mathlib snapshot in `lean-toolchain`)
- [ ] Same random seeds (default `--seed 2026` in 10b/10c/10g/11)
- [ ] `tests/` 58 passed / 3 skipped, `ruff` clean

The headline numbers (Phase 7 = 57.0%, Phase 9 monitor F1 = 0.871,
axiom_audit fix → 100% recall on `implementation_leak`) are reproduced by
re-running steps 5–7 of `reproduce.sh` from the restored tarballs.
