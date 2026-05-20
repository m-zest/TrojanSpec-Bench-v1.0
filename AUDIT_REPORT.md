# TrojanSpec-Bench-v1.0 — End-to-End Audit Report

_Audit performed 2026-05-20 against working tree at HEAD = `76c0425` (latest tag `v0.3.0`)._

> **NOTE — discrepancy with the audit brief.** The brief says "the current release is v0.2.0 (commit 21cb74e)". The repository's actual HEAD is `76c0425` and `git tag` shows `v0.3.0` (see Pass 7). I audited what is on disk now, not v0.2.0. If you intended me to audit v0.2.0 specifically, the report would need to be re-run after `git checkout v0.2.0`.

---

## Pass 10 — Executive summary

### Audit footprint

| Metric | Value |
|---|---:|
| Total files audited (excluding `venv/`, `.git/`, tarballs) | **178** |
| Working-tree size (excluding `venv/`, `.git/`) | **8.4 MB** |
| Python files in `src/` | **43** (4,261 LOC) |
| Python files in `scripts/` | **27** (4,882 LOC) |
| Total Python LOC | **9,143** |
| `.md` docs audited | **14** (incl. root + `docs/`) |
| `.json` data files opened | **23** (every file in `data/`) |
| `.jsonl` data files line-counted + sampled | **5** |
| Tests collected (static count) | ~**58** (54 raw `def test_*`, ~4 from parametrize expansion) |
| Tests passed / failed / skipped | **NOT VERIFIED** — `venv/` is not present in the working tree; brief said skip if absent |
| Inconsistencies / cosmetic deviations found (Pass 8) | **9** (3 minor numeric, 1 real prose error, 2 doc-vs-SUMMARY, 1 ratio rounding, 1 attack-threshold mislabel, 1 version drift across 3 strings) |
| Real factual gaps (Pass 8) | **2** (no Phase 11 atomic FPR; no cross-vendor attacker partition) |
| Risk-register items (Pass 9) | **16** |

### Top 5 things to fix before paper submission

1. **`.env.example` is missing AWS_* keys.** HANDOFF and `scripts/reproduce.sh` tell the reviewer to copy `.env.example` to `.env` and set `AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_DEFAULT_REGION`, but the template only declares Fireworks/OpenRouter/Anthropic/OpenAI/Ollama/HF keys. Bedrock — which is what the entire headline pipeline runs on — gets no slot. **Fix:** append the three AWS variables (with empty values + a one-line comment) to `.env.example`. 3 lines, no risk.

2. **The reproducer branch no longer exists on origin.** `HANDOFF.md` L18 and L385, `scripts/reproduce.sh` L6, and `scripts/run_phase10_phase11.sh` L15 all reference `claude/professional-search-interface-MCp22`. That branch has been merged into `main` (via PR #16) and deleted; a reviewer running `git checkout claude/professional-search-interface-MCp22` will get a pathspec error. **Fix:** replace with `v0.3.0` (or `main`) in all 4 places. Decide whether `v0.3.0` or a new `v0.4.0` (tagging HEAD) is the canonical release.

3. **Three different version strings.** `pyproject.toml` says `1.0.0`; `HANDOFF.md` says `v0.2.0 / 21cb74e`; `git tag` shows `v0.3.0`; `docs/hf_dataset_card.md` changelog confirms `v0.3.0 (2026-05-20)`. **Fix:** decide on one canonical version, update the other surfaces, and add a one-line `CHANGELOG.md` so a reviewer can see what changed between tags. The HANDOFF version reference is **9 commits stale** and is the most visible inconsistency.

4. **Phase 11 Mathlib never runs the headline atomic_monitor.** `data/phase11_summary.json` reports only `axiom_audit_flag_rate (0.0)` and `monitor_consensus_flag_rate (0.23)`. The Phase 10i atomic K=2 detector — the entire paper headline — has never been evaluated against the honest-formal-mathematics calibration set. If a reviewer asks "what is the K=2 detector's FPR on real Mathlib?" there is no answer in the artifacts. **Fix:** rerun `scripts/11_mathlib_case_study.py` with atomic_monitor added (~100 lemmas × 4 atomic criteria × 1 monitor ≈ 400 Bedrock calls; cost ≈ $0.30, runtime ≈ 10 min). This single experiment closes the most reviewable gap in the paper.

5. **`scripts/run_phase10_phase11.sh` hardcodes personal author + auto-pushes after every stage.** `gitci()` runs `-c user.name="Mohammad Zeeshan" -c user.email="hdglit@inf.elte.hu" --author=...` and then `git push origin "$BR"`. Anyone reproducing on a fork will (a) mint commits attributed to Mohammad Zeeshan and (b) hit a push failure since the branch is stale. Both are visible to any reviewer who reads the script. **Fix:** strip the identity override, remove the `git push` lines, and document the commit/push step in HANDOFF as a manual user action.

### Honorable mentions (not in the top 5, but quick wins)

6. `docs/phase10i_atomic_monitor.md` L138 says "**95% of honest specs fail < 2 criteria**"; actual is **93.16%** (954/1024). Off by 2 pp in prose — a reviewer with a calculator will catch this immediately.
7. "4.4× FPR reduction" in HANDOFF/README — computed ratio is **4.342×**, not 4.4. Round honestly to 4.3× or 4×.
8. `docs/threat_model.md` says Phase 5b generated 300 triples with 75 per attack pattern; the SUMMARY (and every other doc) says 298 / {75, 75, 75, **73**}. Two-of-300 yield gap not propagated into the threat-model prose.
9. Delete (or `.gitignore`) the 829 KB strategic-analysis PDF at the repo root — unless that's intended public output.
10. Atomic_monitor isn't a library module (`src/trojanspec/specguard/atomic_monitor.py` doesn't exist); it lives entirely in `scripts/10i_atomic_monitor.py`. Promote it to `src/` so unit tests, the HF Space, and downstream users can import it.

### What this audit could **not** verify

- **Tests pass/fail/skip counts.** `venv/` absent, system python has no pytest, brief forbade recreating venv. Static collection suggests ~58 tests; HANDOFF claims "58 passed / 3 skipped". Not run.
- **Whether the v1/v4 tarballs unpack to the documented per-attack distributions.** The individual triple JSONs are `.gitignore`d and only live inside the tarballs. I substituted by counting `attack_pattern` tags across `phase9_results_v2.jsonl` (one record per admitted triple); the distribution matches HANDOFF §2 exactly (377/348/187/112 = 1024). But the raw triples themselves were not unpacked or inspected.
- **Bedrock-billed scripts.** Brief forbade re-running them. All headline numbers (Phase 7, 9, 10a–10i, 11) were verified against committed JSON / JSONL, not re-derived.

### Overall assessment

The benchmark's **headline numbers all reconcile** between README, HANDOFF, the per-phase docs, and the source JSON files — to the precision claimed. Phase 10i (atomic-criteria K=2-of-4, F1 0.967, 5-fold CV 0.967 ± 0.005, FPR 0.068, K* = 2 on every fold) verifies exactly. Phase 7 admission (57.0%, Dafny+Lean 61.3%) verifies exactly. Phase 9 detector metrics, Phase 10a–10h ablations, Phase 11 Mathlib FPR — all verify.

What's wrong is mostly **reproducibility surface**, not science: the `.env.example` template, the dead-branch references in three orchestration scripts, and the version-string drift. None of these change the paper's numbers; all of them will trip up a fresh-server reviewer in the first 10 minutes.

The one **scientific gap** worth closing before submission is **Phase 11 atomic-monitor FPR on Mathlib** — the headline detector has not been tested on the honest-formal-mathematics calibration set, even though `axiom_audit` and `monitor_consensus` have been. That's a 10-minute, $0.30 fix that materially strengthens the paper.

---

## Pass 1 — Inventory

### Totals

- Files (after excluding `.git/`, `venv/`, `__pycache__/`, `.lake/`, `data/v?_backup_*` per the brief's `find` invocation): **178**
- Disk size of the working tree (excluding `venv` and `.git`): **8.4 MB**
- Disk size including `.git`: **13 MB**
- `venv/` is **not present** in the working tree. This blocks Pass 4 (the brief says "If venv is not present, say so and skip").

### Count and size by top-level directory

| Path                | Files | Size |
| ------------------- | ----: | ---: |
| `src/`              |    44 | 272K |
| `scripts/`          |    39 | 300K |
| `tests/`            |    14 |  64K |
| `data/`             |    40 | 6.2M |
| `docs/`             |    12 |  92K |
| `figures/`          |     9 | 528K |
| `hf_space_build/`   |    11 |  72K |
| `notebooks/`        |     1 |  4.0K |
| `.github/`          |     2 |  16K |

Root-level files: `.env.example`, `.gitignore`, `HANDOFF.md`, `LICENSE`, `README.md`, `STATUS.md`, `pyproject.toml`, `TrojanSpec-Bench vs SPS-Control_ Strategic Analysis for the Secure Program Synthesis Hackathon.pdf`.

### Things flagged in Pass 1

1. **`data/triples/` and `data/triples_xfamily/` do not contain the actual triples.** The brief assumes 1024 + 298 individual triple JSONs are present. They are not. The two directories together contain only:
   - `data/triples/.gitkeep` (0 bytes)
   - `data/triples/phase5a_SUMMARY.json` (561 bytes)
   - `data/triples_xfamily/.gitkeep` (0 bytes)
   - `data/triples_xfamily/phase5b_SUMMARY.json` (611 bytes)

   The only individual triple JSONs in the repo are under `data/triples_sanity/`, and there are **10** of them (4 dafny/hard, 3 lean/hard, 3 verus/hard). This will make Pass 8 #7 (per-attack-pattern counts by sampling triples) impossible to do from the working tree — those counts can only be checked via the SUMMARY files or by extracting one of the backup tarballs. **Flag.**

2. **Two large backup tarballs are tracked in git** (despite being excluded from the brief's `find`):
   - `data/v1_backup_20260518_003516.tar.gz` — 511 KB
   - `data/v4_backup_20260519_224805.tar.gz` — 791 KB

   Both appear in `git ls-files`. They account for the bulk of `data/`'s 6.2 MB. The brief mentions the bdf082f Verus binary leak; these are not the Verus binary, but they ARE binary artifacts committed inside the data directory. I have not opened them.

3. **A 829 KB PDF is tracked at the root**: `TrojanSpec-Bench vs SPS-Control_ Strategic Analysis for the Secure Program Synthesis Hackathon.pdf`. Filename has a colon-like character (`_`) replacing a real `:`, suggesting it was uploaded from a different OS. Committing strategic analyses into a public repo may not be intended.

4. **Empty placeholder directories kept by `.gitkeep`**:
   - `data/triples/.gitkeep`
   - `data/triples_xfamily/.gitkeep`
   - `figures/.gitkeep` (figures dir is NOT empty; the .gitkeep is leftover)
   - `notebooks/.gitkeep` (the dir contains only the .gitkeep; no notebooks)

5. **No stray temp/editor files found.** I searched for `.DS_Store`, `*.swp`, `*.swo`, `*.bak`, `*.tmp`, `*~`, `Thumbs.db` and found none. No leaked Verus binary, no `__pycache__`, no `.lake/` build dirs.

6. **No untracked Python files** in src/ or scripts/ (full untracked listing in Pass 7).

7. **Largest files in the working tree** (>1 MB), excluding `.git/` and `venv/`:
   - `data/phase9_results_v2.jsonl` — 2.1 MB
   - `data/phase9_results.jsonl` — 2.0 MB
   - The PDF (0.8 MB) and the two tarballs are smaller than 1 MB individually.

8. **No `notebooks/`** — directory exists but contains only `.gitkeep`, despite the README/HANDOFF apparently implying there may be notebooks. (Will re-check in Pass 5.)

---

## Pass 2 — Code reading (src/trojanspec/ and scripts/)

### Totals

- Python files: **70** (43 in `src/trojanspec/`, 27 in `scripts/`)
- Total lines: **9,143** (`src/` 4,261 + `scripts/` 4,882)
- All files have `mtime` = **2026-05-20** (single git checkout day — every file shows the same modification time)
- AST parse errors: **0**
- Largest source files: `src/trojanspec/utils/llm_clients.py` (515), `src/trojanspec/generators/attacks/few_shot.py` (442), `src/trojanspec/specguard/axiom_audit.py` (123)
- Largest scripts: `scripts/10i_atomic_monitor.py` (555), `scripts/_phase9_report.py` (395), `scripts/02_generate_triples.py` (402), `scripts/13_hf_dataset_release.py` (338), `scripts/10h_beat_ssc.py` (331), `scripts/demo_gradio.py` (335)

### Method note

The brief asked me to "open with view and report" for every file. With 70 files this exceeds the per-pass budget. I ran a single Python pass (`/tmp/audit_pass2.py`) that opens each file with `path.read_text()`, parses it with `ast`, and emits per-file imports/classes/functions/stubs/excepts plus regex scans for TODO/FIXME/XXX/HACK, hardcoded paths/credentials/model IDs/AWS regions, and lines >120 chars. Every file is opened. The per-file purpose is the first non-empty line of the module docstring.

### Per-file table

| Path | LOC | classes | top-level fns | One-line purpose |
|---|---:|---:|---:|---|
| `src/trojanspec/__init__.py` | 24 | 0 | 0 | TrojanSpec-Bench: adversarial specification elicitation for AI-assisted… |
| `src/trojanspec/cli.py` | 81 | 0 | 5 | `trojanspec` CLI: inspect the schema, registry, and dataset stats. |
| `src/trojanspec/loaders.py` | 89 | 0 | 2 | Source-problem loaders. |
| `src/trojanspec/schemas.py` | 154 | 6 | 1 | Pydantic data models for TrojanSpec-Bench. |
| `src/trojanspec/crypto/__init__.py` | 12 | 0 | 0 | Cryptographic anchors. |
| `src/trojanspec/crypto/aes_gcm.py` | 123 | 0 | 0 | AES-GCM-128 / 256 attack templates. |
| `src/trojanspec/crypto/anchor.py` | 36 | 1 | 0 | `CryptoAnchor` value type. |
| `src/trojanspec/crypto/anchor_registry.py` | 66 | 0 | 2 | Central `(primitive, attack, language) → CryptoAnchor` registry. |
| `src/trojanspec/crypto/chacha20_poly1305.py` | 104 | 0 | 0 | ChaCha20-Poly1305 attack templates. |
| `src/trojanspec/crypto/ed25519.py` | 52 | 0 | 0 | Ed25519 attack template. |
| `src/trojanspec/crypto/ml_dsa.py` | 137 | 0 | 0 | ML-DSA-44/65/87 (Dilithium) attack templates. |
| `src/trojanspec/crypto/ml_kem.py` | 187 | 0 | 0 | ML-KEM-512/768/1024 attack templates. |
| `src/trojanspec/crypto/sha3.py` | 56 | 0 | 0 | SHA-3 / Keccak attack template. |
| `src/trojanspec/crypto/slh_dsa.py` | 52 | 0 | 0 | SLH-DSA (SPHINCS+) attack template. |
| `src/trojanspec/crypto/x25519.py` | 58 | 0 | 0 | X25519 attack template. |
| `src/trojanspec/generators/__init__.py` | 2 | 0 | 0 | Adversarial spec-eliciting generators and the review/validation drivers. |
| `src/trojanspec/generators/attacks/__init__.py` | 30 | 0 | 0 | The four named attack patterns. |
| `src/trojanspec/generators/attacks/base.py` | 225 | 2 | 2 | Shared machinery for the four attack generators. |
| `src/trojanspec/generators/attacks/domain_restriction.py` | 64 | 0 | 1 | Domain-restriction attack. |
| `src/trojanspec/generators/attacks/few_shot.py` | 442 | 0 | 1 | Few-shot worked examples (4 attacks × 3 languages). |
| `src/trojanspec/generators/attacks/implementation_leak.py` | 64 | 0 | 1 | Implementation-leak attack. |
| `src/trojanspec/generators/attacks/predicate_swap.py` | 67 | 0 | 1 | Predicate-swap attack. |
| `src/trojanspec/generators/attacks/vacuity.py` | 64 | 0 | 1 | Vacuity attack. |
| `src/trojanspec/generators/elicitor.py` | 141 | 1 | 3 | Adversarial spec-eliciting driver. |
| `src/trojanspec/generators/reviewer.py` | 78 | 0 | 7 | Programmatic helpers for the human-review stage. |
| `src/trojanspec/generators/validator.py` | 113 | 0 | 4 | Automated trojan-witness validation. |
| `src/trojanspec/specguard/__init__.py` | 73 | 0 | 1 | SpecGuard: five detectors that flag adversarial specs. |
| `src/trojanspec/specguard/axiom_audit.py` | 123 | 1 | 1 | Axiom-audit detector (all three languages). |
| `src/trojanspec/specguard/base.py` | 84 | 3 | 1 | Shared types for SpecGuard detectors. |
| `src/trojanspec/specguard/ghost_leakage.py` | 67 | 1 | 0 | Ghost-leakage detector. |
| `src/trojanspec/specguard/monitor_consensus.py` | 101 | 1 | 2 | Monitor-consensus detector. |
| `src/trojanspec/specguard/mutation_coverage.py` | 66 | 1 | 1 | Mutation-coverage detector (static proxy). |
| `src/trojanspec/specguard/vacuity_detector.py` | 54 | 1 | 0 | Vacuity detector. |
| `src/trojanspec/utils/__init__.py` | 7 | 0 | 0 | Shared utilities. |
| `src/trojanspec/utils/json_extract.py` | 121 | 1 | 3 | Robust JSON extraction from LLM responses. |
| `src/trojanspec/utils/llm_clients.py` | 515 | 9 | 4 | Unified LLM client interface. |
| `src/trojanspec/utils/logging.py` | 30 | 0 | 1 | Dependency-free logging for the pipeline. |
| `src/trojanspec/utils/wilson_ci.py` | 31 | 0 | 1 | Wilson score interval. |
| `src/trojanspec/verifiers/__init__.py` | 61 | 1 | 1 | Subprocess wrappers around the three verifiers. |
| `src/trojanspec/verifiers/compose.py` | 159 | 0 | 7 | Compose v2 witness body + v2 contract into one program. |
| `src/trojanspec/verifiers/dafny.py` | 78 | 0 | 1 | Dafny verifier subprocess wrapper. |
| `src/trojanspec/verifiers/lean.py` | 105 | 0 | 3 | Lean 4 verifier subprocess wrapper. |
| `src/trojanspec/verifiers/verus.py` | 65 | 0 | 1 | Verus verifier subprocess wrapper. |
| `scripts/02_generate_triples.py` | 402 | 0 | 9 | Phase 5 generation. |
| `scripts/03_review_triples.py` | 133 | 0 | 0 | Phase 6 Streamlit review (top-level Streamlit script, no functions). |
| `scripts/04_validate_witnesses.py` | 218 | 0 | 4 | Phase 7 verifier validation (the sole admission filter). |
| `scripts/05_specguard.py` | 45 | 0 | 1 | SpecGuard CLI over a triple JSON. |
| `scripts/06_phase9_eval.py` | 162 | 0 | 3 | Phase 9 SpecGuard detector evaluation. |
| `scripts/10a_elicitor_sweep.py` | 129 | 0 | 4 | Phase 10a elicitor sweep. |
| `scripts/10b_monitor_temperature.py` | 96 | 0 | 2 | Phase 10b monitor temperature. |
| `scripts/10c_monitor_count.py` | 149 | 0 | 3 | Phase 10c monitor count. |
| `scripts/10d_ensemble_grid.py` | 146 | 0 | 3 | Phase 10d detector-ensemble grid search. |
| `scripts/10e_cross_language.py` | 128 | 0 | 3 | Phase 10e cross-language transfer. |
| `scripts/10f_ssc_baseline.py` | 177 | 0 | 4 | Phase 10f SSC baseline. |
| `scripts/10g_adaptive_attack.py` | 199 | 0 | 3 | Phase 10g adaptive-attack stress test. |
| `scripts/10h_beat_ssc.py` | 331 | 0 | 9 | Phase 10h: can we beat SSC. |
| `scripts/10i_atomic_monitor.py` | 555 | 0 | 20 | Phase 10i atomic-criteria monitor. |
| `scripts/11_mathlib_case_study.py` | 181 | 0 | 3 | Phase 11 Mathlib case study. |
| `scripts/13_hf_dataset_release.py` | 338 | 0 | 5 | Phase 13 HuggingFace dataset release. |
| `scripts/_diag_implleak.py` | 29 | 0 | 0 | Diagnose 3 failed implementation_leak sanity triples. |
| `scripts/_phase10_report.py` | 181 | 0 | 2 | Consolidate Phase 10 ablations into docs/phase10_ablations.md. |
| `scripts/_phase11_report.py` | 90 | 0 | 1 | Build the Phase 11 Mathlib case study report. |
| `scripts/_phase5_summary.py` | 65 | 0 | 1 | Per-phase generation manifest. |
| `scripts/_phase9_axiom_replay.py` | 123 | 0 | 4 | Replay axiom_audit (post-fix) over existing Phase 9 outputs. |
| `scripts/_phase9_report.py` | 395 | 0 | 4 | Aggregate Phase 9 results → metrics + figures + markdown. |
| `scripts/_phase_final_report.py` | 100 | 0 | 2 | Write docs/phase5_to_phase8_complete.md (v1 vs v2 comparison). |
| `scripts/_val_implleak_shapes.py` | 77 | 0 | 0 | Validate candidate implementation_leak shapes (Dafny A/B, Lean A/B). |
| `scripts/_val_lean_fewshot.py` | 58 | 0 | 0 | Validate all 8 Lean few-shot examples through compose(). |
| `scripts/_val_lean_leak_repair.py` | 40 | 0 | 0 | Validate Lean implementation_leak repair. |
| `scripts/demo_gradio.py` | 335 | 0 | 7 | SpecGuard atomic-criteria Gradio HF Space demo. |

### TODO / FIXME / XXX / HACK comments

**Total: 0.** No file in `src/` or `scripts/` contains a `# TODO`, `# FIXME`, `# XXX`, or `# HACK` comment. (Either the codebase was cleaned, or no markers are used as a convention.)

### Stub function bodies (`pass`, `raise NotImplementedError`, docstring-only, bare return)

**Total: 1, intentional.**

- `src/trojanspec/utils/llm_clients.py:93` — `LLMClient.complete` raises `NotImplementedError`. This is an abstract method on the base class; subclasses (`OpenRouterClient`, `FireworksClient`, `OpenAIClient`, `AnthropicClient`, `BedrockClient`, `OllamaClient`) override it. Not a missing implementation.

### Bare or broad `except:` clauses (14 total)

| File | Line | Form |
|---|---:|---|
| `src/trojanspec/cli.py` | 48 | `except Exception` (no re-raise) |
| `src/trojanspec/specguard/__init__.py` | 45 | `except Exception` (no re-raise) |
| `src/trojanspec/specguard/monitor_consensus.py` | 66 | `except Exception` (no re-raise) |
| `scripts/02_generate_triples.py` | 194 | `except Exception` (no re-raise) |
| `scripts/02_generate_triples.py` | 330 | `except Exception` (no re-raise) |
| `scripts/04_validate_witnesses.py` | 184 | `except Exception` (no re-raise) |
| `scripts/06_phase9_eval.py` | 122 | `except Exception` (no re-raise) |
| `scripts/10b_monitor_temperature.py` | 27 | `except Exception` (no re-raise) |
| `scripts/10c_monitor_count.py` | 53 | `except Exception` (no re-raise) |
| `scripts/10g_adaptive_attack.py` | 64 | `except Exception` (no re-raise) |
| `scripts/10i_atomic_monitor.py` | 119 | `except Exception` (no re-raise) |
| `scripts/10i_atomic_monitor.py` | 201 | `except Exception` (no re-raise) |
| `scripts/11_mathlib_case_study.py` | 121 | `except Exception` (no re-raise) |
| `scripts/demo_gradio.py` | 54 | `except Exception` (no re-raise) |

No `except:` (truly bare) clauses. All are `except Exception:` without re-raise. Several look intentional (per-triple isolation in batch loops, monitor-call failures in `monitor_consensus`) but they swallow real errors silently and are worth a code-review pass before paper submission.

### `print(...)` calls in library code (`src/`)

**Total: 8, all in `src/trojanspec/cli.py`** (the CLI entry point — these are expected output, not stray debug prints):

- L20 `print(json.dumps(Triple.model_json_schema(), indent=2))`
- L25 `print("Available LLM families:")`
- L27 `print(f"  - {fam}")`
- L32 `print(f"{len(ANCHORS)} cryptographic anchors registered:")`
- L36 `print(f"  {prim.value:14s} {atk.value:22s} {lang.value:6s}  <- {anchor.bug_source}")`
- L51 `print(f"data dir : {data_dir}")`
- L52 `print(f"triples  : {total}")`
- L53 `print(f"admitted : {admitted}")`

No `print()` in any non-CLI library file. Good.

### Lines longer than 120 chars

**Total: 10, across 8 files.**

| File | Long lines |
|---|---:|
| `scripts/_val_lean_fewshot.py` | 3 |
| `scripts/10c_monitor_count.py` | 1 |
| `scripts/10f_ssc_baseline.py` | 1 |
| `scripts/10h_beat_ssc.py` | 1 |
| `scripts/13_hf_dataset_release.py` | 1 |
| `scripts/_phase10_report.py` | 1 |
| `scripts/_phase9_report.py` | 1 |
| `src/trojanspec/specguard/axiom_audit.py` | 1 |

Cosmetic. Probably the project does not enforce a line-length lint.

### Hardcoded AWS regions

**Total: 2 occurrences, both `us-east-1`.**

- `scripts/demo_gradio.py:25` — `us-east-1` (hardcoded as a literal). Not read from env.
- `src/trojanspec/utils/llm_clients.py:282` — `self._region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")` (used only as fallback default; env-var wins).

`demo_gradio.py` should probably also read from `AWS_DEFAULT_REGION` rather than hardcode. **Flag.**

### Hardcoded model IDs

The codebase has many model-ID literals — they're not hidden, they're the family registry. The canonical mapping lives in `src/trojanspec/utils/llm_clients.py:451-496`. Notable ID-bearing files:

- `src/trojanspec/utils/llm_clients.py` — 19 unique IDs (canonical family registry). Includes both the "cross-region inference profile" IDs (`us.anthropic.claude-sonnet-4-6`, `us.anthropic.claude-haiku-4-5-20251001-v1:0`, `us.meta.llama3-3-70b-instruct-v1:0`) and the bare-id fallbacks, plus Fireworks/OpenRouter/Ollama/Anthropic/OpenAI alternatives. The `claude-3-5-sonnet-latest` (L494) is the **legacy default for the `anthropic` family** — confirm if this should now be Claude 4.6/4.7 for the paper.
- `src/trojanspec/specguard/monitor_consensus.py` — 4 family names referenced in the monitor panel (`claude-sonnet`, `claude-haiku`, `llama-70b`).
- `scripts/13_hf_dataset_release.py:30-35` — model IDs embedded in dataset metadata.
- `scripts/02_generate_triples.py`, `10b/10c/10f/10g/10h/10i`, `11_mathlib_case_study.py`, `demo_gradio.py` — each passes a specific family name as a string. None look like a bug; flagged only because the brief asked for the list.

### Hardcoded absolute paths

**Total: 0.** No `/home/...`, `/usr/...`, `/var/...`, `/tmp/...`, or `C:\...` string literals in any source file. The codebase uses `pathlib.Path` everywhere relative to module root or CLI argument.

### Hardcoded credentials

**Total: 0.** No `sk-...` API keys, no `AKIA...` AWS access keys, no `api_key="..."` literals, no `password="..."` literals.

### Pass-2 conclusions

- The codebase is small and tidy: no TODO/FIXME markers, no path/credential leaks, only 1 abstract-method "stub" (intentional), 10 over-long lines (cosmetic).
- The 14 `except Exception` clauses are the main code-quality smell — most look like deliberate per-item failure isolation in batch loops, but it would be worth a one-pass code review to confirm none are masking real bugs in `monitor_consensus`.
- The 5 detectors confirmed in `src/trojanspec/specguard/` are: `vacuity_detector.py`, `mutation_coverage.py`, `ghost_leakage.py`, `axiom_audit.py`, `monitor_consensus.py`. The README's "5 detectors" matches; the HANDOFF "6 detectors" statement (if it exists — verified in Pass 8) does not.
- `scripts/03_review_triples.py` defines no top-level functions because it is a top-of-script Streamlit page; functionality is in module-scope code. Will not collect with pytest.

---

## Pass 3 — Data files

### Method

Every JSON listed in the brief was opened and parsed. JSONL files were line-counted and 3–5 random lines were sampled. Triples directories were directly inspected.

### `data/phase7_admission_report.json`

| Top-level key | Value |
|---|---|
| `total` | 1798 |
| `admitted` | 1024 |
| `admission_pct` | 57.0 |
| `by_language.verus` | admitted 288 / total 598 = **48.2%** |
| `by_language.lean` | admitted 417 / total 600 = **69.5%** |
| `by_language.dafny` | admitted 319 / total 600 = **53.2%** |
| `by_attack.implementation_leak` | 377 / 450 = 83.8% |
| `by_attack.domain_restriction` | 187 / 450 = 41.6% |
| `by_attack.vacuity` | 348 / 450 = 77.3% |
| `by_attack.predicate_swap` | 112 / 448 = 25.0% |
| `by_model` Sonnet | 906 / 1500 = 60.4% |
| `by_model` Haiku | 59 / 148 = 39.9% |
| `by_model` Llama | 59 / 150 = 39.3% |

**Cross-check against HANDOFF.md §5.** HANDOFF claims "**57.0%** (1024/1798); Dafny+Lean 61.3%". File confirms 1024/1798 = 57.0%. Dafny+Lean derived from JSON: (319+417)/(319+417+281) = 736/1200 = **61.33%** → ✓ matches. Per-attack distribution claim in HANDOFF §2 ("implementation_leak 377, vacuity 348, domain_restriction 187, predicate_swap 112") matches exactly.

### `data/phase9_metrics.json` (V1, pre-fix)

- `n_triples` = 1024.
- `per_detector.axiom_audit`: **tp 0, fp 0, tn 1024, fn 1024, P 0.0, R 0.0, F1 0.0** — the pre-fix zero-recall state mentioned in STATUS.

### `data/phase9_metrics_v2.json` (V2, post-fix; the headline file)

Five detectors, full counts:

| Detector | TP | FP | TN | FN | P | R | F1 | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `vacuity` | 57 | 0 | 1024 | 967 | 1.000 | 0.0557 | 0.1055 | 0.000 |
| `mutation_coverage` | 235 | 0 | 1024 | 789 | 1.000 | 0.2295 | 0.3733 | 0.000 |
| `ghost_leakage` | 148 | 0 | 1024 | 876 | 1.000 | 0.1445 | 0.2526 | 0.000 |
| `axiom_audit` | 377 | 131 | 893 | 647 | 0.7421 | 0.3682 | 0.4922 | 0.1279 |
| `monitor_consensus` | 1024 | 304 | 720 | 0 | 0.7711 | 1.000 | 0.8707 | 0.2969 |

- `overall.auc` = 0.793
- `overall.paired_mean_risk_delta` = 0.4395 (HANDOFF says "+0.440" — ✓ to 3 dp)
- `overall.paired_discrimination_rate` = 0.5859
- `per_attack.axiom_audit.implementation_leak` = 377/377 = **1.000** (matches HANDOFF "R=1.000 on impl_leak").
- `monitor_cross_contamination.bedrock-llama-70b.llama.miss_rate` = 0.0000 (HANDOFF §8 "Llama monitor miss_rate on Llama-generated trojans is 0.000" ✓)
- `monitor_cross_contamination.bedrock-llama-70b.haiku.miss_rate` = 0.0169 (1/59 → small but not zero; HANDOFF rounds this away)

**Cross-check vs HANDOFF §4.3 detector table.** All five rows match to the displayed precision.

### `data/phase9_results_v2.jsonl`

- **1024 lines.** I scanned every line to count tags.
- Per-attack-pattern counts in the JSONL: `implementation_leak: 377, vacuity: 348, domain_restriction: 187, predicate_swap: 112` (sum = 1024) → **exactly matches** HANDOFF §2 and the SUMMARY.
- Per-language: `verus: 288, lean: 417, dafny: 319` (sum = 1024) ✓.
- Per-elicitor: `sonnet: 906, haiku: 59, llama: 59` ✓.
- Three random sample triple_ids: `4393f453-78a5-48f4-99e1-fbd193c3c1bb` (verus/vacuity/sonnet/vericoding), `7f9189e8-f448-4af1-bb5c-fb11205c7b03` (verus/implementation_leak/sonnet/vericoding), `b09f16de-e770-45c2-9635-189fdab8c1cf` (lean/vacuity/sonnet/humaneval). Each record carries a full `trojan` and `honest` block with the 5-detector verdict array — well-formed.

### `data/phase10_10a_elicitor_sweep.json`

Top-level: `by_elicitor` with sub-buckets `all`, `sonnet`, `haiku`, `llama`. Each has `n`, `per_detector` (5 detectors with the same 7-field schema as phase9_metrics_v2), `paired_mean_risk_delta`, `paired_discrim_rate`.

- `all.n = 1024`, `sonnet.n = 906`, `haiku.n = 59`, `llama.n = 59`.
- HANDOFF claim "Haiku trojans easier (ghost_leakage R 0.593 vs 0.117 on Sonnet)" → JSON: `haiku.ghost_leakage.recall = 0.5932`, `sonnet.ghost_leakage.recall = 0.117`. ✓ (HANDOFF rounded to 3 dp).
- HANDOFF claim "Llama tracks Sonnet" → `llama.monitor_consensus.f1 = 0.8741` vs `sonnet.monitor_consensus.f1 = 0.8691`. Plausible.

### `data/phase10_10b_temperature.json`

- `n = 200`, `temps = [0.0, 0.3, 0.7, 1.0]`.
- For each temperature: `unfaithful = 200, faithful = 0, abstain = 0, unfaithful_rate = 1.0, agree_with_default = 1.0`.
- Every vote in every temperature bucket is the string `"unfaithful"`.
- **HANDOFF "100% temperature-stable (200/200 UNFAITHFUL at temps 0.0/0.3/0.7/1.0)" → ✓ exact.**

### `data/phase10_10c_monitor_count.json`

- `sample = 300`, three panels.
- Panel sizes/F1:

| Size | Composition | TP-flagged | Honest-flagged | P | R | F1 | FPR |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | Sonnet@0.7 | 300 | 66 | 0.8197 | 1.000 | **0.9009** | 0.220 |
| 3 | Sonnet+Haiku+Llama @ 0.7 | 300 | 67 | 0.8174 | 1.000 | 0.8996 | 0.2233 |
| 5 | (3) + Sonnet@0, Haiku@0 | 300 | 67 | 0.8174 | 1.000 | 0.8996 | 0.2233 |

- **HANDOFF claim "1 = 3 = 5 in F1 (all 0.900–0.901)" — actual range is 0.8996 → 0.9009. Within the "all 0.900–0.901" envelope only if you round 0.8996 up to 0.900. Mild rounding licence; flag in Pass 8.**

### `data/phase10_10d_ensemble_grid.json`

- `n_records = 1024`. `grid` has 32 entries (subsets of {vacuity, mutation_coverage, ghost_leakage, axiom_audit, monitor_consensus}).
- `best_by_f1.subset = ["monitor_consensus"]`, F1 = 0.8707, cost = 3.
- `cheapest_at_best_f1.subset = ["monitor_consensus"]`, same F1, cost = 3.
- When `axiom_audit` is added to monitor_consensus, F1 drops to **0.8285** (HANDOFF says "0.829" → ✓).

### `data/phase10_10e_cross_language.json`

- `n_records = 1024`. `per_language_n = {verus 288, lean 417, dafny 319}`.
- `thresholds_chosen.{dafny,lean,verus} = 0.75` — identical across languages (✓ HANDOFF "threshold identical 0.750").
- In-language F1 by language:
  - Dafny: **0.9953** (P 0.9907, R 1.000, FPR 0.0094)
  - Lean: **0.851** (P 0.7407, R 1.000, FPR 0.3501)
  - Verus: **0.6769** (P 0.5115, R 1.000, FPR 0.9549)
- Spread = 0.9953 − 0.6769 = **0.3184** (HANDOFF says spread "0.31" → ✓).
- Cross-language tables (applied_to) are identical across train languages — i.e., applying any language's threshold (all 0.75) gives the same numbers. Makes sense given identical threshold.

### `data/phase10_10f_ssc_summary.json`

- `n=1024, tp=1024, fp=304, tn=720, fn=0, P=0.7711, R=1.000, F1=0.8707, FPR=0.2969`.
- **HANDOFF "P=0.771 R=1.000 F1=0.871 FPR=0.297" — ✓ to 3 dp.**
- `baseline_note`: "SSC asks one model two paraphrased questions; flag = disagreement or both UNFAITHFUL."

### `data/phase10_10f_ssc_results.jsonl`

- **1024 lines.** First-record keys: `triple_id, attack_pattern, language, trojan, honest`. Per-record `trojan` and `honest` contain SSC verdicts.

### `data/phase10_10g_adaptive.json`

- `sampled = 60`, `model_followed_constraint = 60`, `admitted_after_reverify = 57`, `admitted_pct = 0.95`.
- `static_detector_catch_on_admitted = {vacuity 3, mutation_coverage 16, ghost_leakage 0, axiom_audit 18}` (out of 57 admitted).
- `axiom_audit_recall_on_adaptive = 0.3158` (18 / 57 ≈ 0.3158).
- `note` quoted: "Baseline (Phase 9): axiom_audit caught 377/377 (100%) of admitted implementation_leak triples. This adaptive run measures whether the same attack semantically expressed without axiom-like markers still slips past axiom_audit while remaining a real weakening."
- **HANDOFF "axiom_audit recall drops 100% → 31.6%; mutation_coverage 28%": axiom_audit ✓ (31.58%); mutation_coverage = 16/57 = 28.07% ✓.**

### `data/phase10_10g_adaptive.jsonl`

- **60 lines.** First-record keys: `triple_id, elicitor_model, language, nl_requirement, original_spec, preamble, result`.

### `data/phase10_10h_beat_ssc.json`

- `h1_static_only`: P 0.793, R 0.4902, F1 **0.6059**, FPR 0.1279. (cost 0)
- `h2_ssc_adaptive`: n=57, ssc_recall 1.000, ssc_fpr_on_honest 0.2982, ssc_precision 0.7703, ssc_f1 **0.8702**.
- `h3_ssc_cross_language`: per-language SSC: Dafny F1 0.9922, Lean F1 0.9698, **Verus F1 0.6784**; `f1_range = 0.3138`, `f1_std = 0.1429`.
- `h4_logreg_ensemble`: 5-fold CV F1 = **0.8705 ± 0.023**. Coefficients: vacuity 2.4744, mutation_coverage 3.2025, ghost_leakage 1.8538, axiom_audit 1.8654, **monitor_consensus 6.0205**, intercept −5.3995.
- `h5_monitor_unanimous`: tp 1021, fp 294, tn 730, fn 3, P 0.7764, R 0.9971, F1 0.873, FPR 0.2871.
- **HANDOFF claim "5 hypotheses tie SSC (F1 0.871)": ✓ all 5 within 0.6 / 0.87/ 0.87 / 0.87 / 0.87 range, none beats SSC by F1.** H1 lags substantially (0.606) but the others tie.

### `data/phase10_10i_atomic.json` (the headline)

- `n_triples = 1024`, `n_side_rows = 2048`, `n_llm_calls = 8192`, `malformed_calls = 0`, `malformed_rate = 0.0`.
- K-of-4 sweep:

| K | TP | FP | TN | FN | P | R | F1 | FPR |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1024 | 310 | 714 | 0 | 0.7676 | 1.000 | 0.8685 | 0.3027 |
| **2** | **1024** | **70** | **954** | **0** | **0.936** | **1.000** | **0.9669** | **0.0684** |
| 3 | 905 | 11 | 1013 | 119 | 0.988 | 0.8838 | 0.933 | 0.0107 |
| 4 | 406 | 0 | 1024 | 618 | 1.000 | 0.3965 | 0.5678 | 0.000 |

- `best_k_full_set = 2`; `best_continuous_full_key = "t=0.375"` → same metrics as K=2.
- 5-fold CV (rule_k): mean test F1 = **0.9668**, std = **0.0049**; **k_star_train = 2 on every fold**.
- Per-language at best K (K=2):
  - Dafny: F1 0.9922 (P 0.9846, R 1.000, FPR 0.0157)
  - Lean: F1 0.9698 (P 0.9413, R 1.000, FPR 0.0624)
  - Verus: F1 0.9366 (P 0.8807, R 1.000, FPR 0.1354)
  - `f1_range = 0.0556`, `f1_std = 0.0228`.
- Per-attack at best K:
  - vacuity: F1 0.9613 (FPR 0.0805)
  - implementation_leak: F1 0.9642 (FPR 0.0743)
  - domain_restriction: F1 0.9816 (FPR 0.0374)
  - predicate_swap: F1 0.9697 (FPR 0.0625)
- Per-criterion alone (single Yes/No criterion):
  - completeness: F1 0.8681
  - independence: F1 0.5624
  - **logical_fidelity (C3): F1 0.9752** ← HANDOFF "C3 alone reaches F1 0.975" ✓
  - consistency: F1 0.9344
- `verdict`: `"WIN: best-K full-set F1=0.967, 5-fold CV F1=0.967 vs SSC F1=0.871/monitor_consensus F1=0.871/ensemble F1=0.871"`.

**Cross-check against HANDOFF §5/§6:** every number on the §6 "what we beat" table — F1 0.967, FPR 0.068, FPR ratio 4.4× (0.297/0.068=4.37), C3-alone F1 0.975, per-language spread 0.056, K* = 2 on every fold, malformed 0/8192 — matches the JSON to the displayed precision. **HANDOFF nit:** §5 says "all 4 attack families ≥ 0.937 at R=1.000". The minimum per-attack F1 is 0.9613 (vacuity), well above 0.937 — so the claim is *true* but the threshold "0.937" looks like it was lifted from the per-language Verus F1 (0.9366) by accident. Cosmetic.

### `data/phase10_10i_atomic_results.jsonl`

- **1024 lines.** Sample record keys: `triple_id, language, attack_pattern, trojan, honest`. The `trojan` and `honest` blocks each contain `per_criterion` (4 criteria with "yes/no"), `failures`, `answered`.

### `data/phase11_summary.json`

```json
{
  "n_theorems": 100,
  "axiom_audit_flag_rate": 0.0,
  "axiom_audit_flagged": 0,
  "monitor_consensus_flag_rate": 0.23,
  "monitor_consensus_flagged": 23,
  "interpretation": "On 100 honest Mathlib lemmas, ..."
}
```

- **HANDOFF claim "100 lemmas → axiom_audit 0/100, monitor_consensus 23/100" → ✓.**
- **GAP (brief Pass 8 #3): the file contains NO `atomic_monitor` FPR on Mathlib.** Only the static `axiom_audit` and the coarse `monitor_consensus`. The headline Phase 10i detector was never run on honest Mathlib. This is a known gap; flagging here and again in Pass 8.

### `data/phase11_results.jsonl`

- **100 lines.** First-record keys: `triple_id, source_file, name, stmt_len, axiom_audit, monitor_consensus`. Three samples:
  - `mathlib::IsDiag.lean::isDiag_conjTranspose_iff` — axiom_audit clean, monitor_consensus clean (1 unfaithful vote → not flagged).
  - `mathlib::Intrinsic.lean::intrinsicInterior_subset` — both clean (0 unfaithful).
  - `mathlib::Intrinsic.lean::intrinsicClosure_nonempty` — axiom_audit clean, monitor_consensus **malicious** (2 unfaithful: Haiku + Llama said unfaithful, Sonnet faithful).

### Triples directories — **major gap**

- `data/triples/.gitkeep` + `data/triples/phase5a_SUMMARY.json` only. The 1024 admitted triple JSONs are **NOT** in the working tree.
- `data/triples_xfamily/.gitkeep` + `data/triples_xfamily/phase5b_SUMMARY.json` only. The 298 cross-family draft triple JSONs are **NOT** in the working tree.
- `data/triples_sanity/{dafny,lean,verus}/hard/` contain a total of **10** sanity-set triple JSONs (4 + 3 + 3).

The SUMMARY files confirm:

| Phase | Expected | Generated | yield | per-language | per-attack | per-model | $ |
|---|---:|---:|---:|---|---|---|---:|
| 5a | 1500 | 1500 | 100.0% | dafny/lean/verus = 500/500/500 | each attack = 375 | Sonnet 1500 | $2.96 |
| 5b | 300 | 298 | 99.3% | dafny/lean/verus = 100/100/98 | pred_swap 73, vacuity 75, impl_leak 75, dom_restr 75 | Haiku 148, Llama 150 | $0.57 |

The SUMMARY note explicitly says: *"Raw triples are git-ignored (regenerated locally); this manifest is the committed record."* So the missing files are intentional — they live in the v1/v4 backup tarballs in `data/`. **The audit brief's Pass 8 #7 plan (count tags by sampling 20 random triples) cannot run against the working tree.** I substituted by counting tags in `phase9_results_v2.jsonl` (which has one record per admitted triple); the counts match HANDOFF §2 exactly. See Pass 8 for the cross-check write-up.

### Sanity reports (v2 → v4)

`data/sanity_v2_report.json`, `v2b`, `v3`: all three identical — **1/10 admitted = 10.0%**, generator was `qwen2.5:32b`. v2-era pre-pivot numbers.

`data/sanity_v4_report.json`: **6/10 admitted = 60.0%**, generator was `us.anthropic.claude-sonnet-4-6`. This is the v4-era confirmation that the Bedrock pivot worked. Per-language: Lean 3/3, Dafny 2/4, Verus 1/3.

### Pass-3 summary findings

- All headline numbers in HANDOFF §5/§6 verified against the JSON files to the precision shown.
- Two minor cosmetic things to flag: Phase 10c HANDOFF says "0.900-0.901" but min is 0.8996; Phase 10i HANDOFF says "all 4 attack families ≥ 0.937" but the actual min is 0.961 (the 0.937 looks borrowed from per-language Verus).
- One real gap: **no atomic_monitor FPR on Mathlib** in `phase11_summary.json`. Phase 11 only ran the static `axiom_audit` and the coarse `monitor_consensus`. This is reportable as a limitation but not a numeric error.
- Phase 9 v1 vs v2 axiom_audit: v1 was `(tp 0, fp 0, fn 1024, F1 0.0)`, v2 is `(tp 377, fp 131, fn 647, F1 0.4922)` — the "post-fix recovery from 0" claim is supported by both files being checked in.

---

## Pass 4 — Tests

### Method note

The brief says "If venv is not present, say so and skip." **`venv/` is not present in the working tree, and the system `python3` has no `pytest` module** (`/usr/bin/python3 -m pytest --version` → `No module named pytest`). I therefore did **not** run pytest. The brief explicitly forbids recreating the venv, so I report the static collection only.

### Static collection (per-file `def test_` and `async def test_` count)

| Path | raw `def test_*` | parametrize-expanded* | Notes |
|---|---:|---:|---|
| `tests/test_json_extract.py` | 6 | 6 | |
| `tests/test_schemas.py` | 3 | 3 | |
| `tests/test_wilson_ci.py` | 4 | 4 | |
| `tests/test_crypto/test_anchors.py` | 3 | 3 | |
| `tests/test_attacks/test_generators.py` | 3 | 3 + 3 extra = 6 | `test_each_attack_parses_fake_response` parametrized over `list(AttackPattern)` = 4 |
| `tests/test_verifiers/test_compose.py` | 7 | 7 | |
| `tests/test_verifiers/test_wrappers.py` | 4 | 5 | `test_graceful_when_tool_absent` parametrized × 2 over `(verify_dafny, "dafny")` / `(verify_verus, "verus")` |
| `tests/test_specguard/test_detectors.py` | 24 | 24 | |
| **Total** | **54** | **~58** | |

*Approximate expansion — exact counts require pytest collection. The expanded total of ~58 is consistent with HANDOFF's claim "pytest 58 passed / 3 skipped" (the 3 skipped are most likely `test_graceful_when_tool_absent[verify_dafny-dafny]`, `test_graceful_when_tool_absent[verify_verus-verus]`, `test_lean_graceful_when_absent` if the verifier tools are installed, OR `test_dafny_accepts_trivial` (marked `@pytest.mark.verifier`) + 2 others if they are not — only one of these scenarios will produce 3 skips).

### Skip mechanism

- `@pytest.mark.verifier` is used once (`test_dafny_accepts_trivial`).
- Within-test runtime skips (`pytest.skip(...)` when `shutil.which(...)` finds/misses a tool) are used in three tests of `tests/test_verifiers/test_wrappers.py`.
- No `conftest.py`-level skip filters are configured; `tests/conftest.py` only defines a `FakeClient` fixture for offline LLM-call mocking.

### Tests vs library coverage

Detectors covered (`tests/test_specguard/test_detectors.py` has 24 tests):
- `vacuity_detector` — 4 tests (pos/pos/neg/neg)
- `mutation_coverage` — 4 tests
- `ghost_leakage` — 4 tests
- `axiom_audit` — 6 tests (one per language family + 2 negatives)
- `monitor_consensus` — 4 tests (offline; uses FakeClient)
- `scan_triple` integration — 2 tests

The 5 detectors named in `src/trojanspec/specguard/` are all exercised. No tests for the Phase 10i atomic-criteria monitor — that detector lives entirely inside `scripts/10i_atomic_monitor.py` (no `src/trojanspec/specguard/atomic_monitor.py` module exists). This is a **structural finding** for Pass 9: the headline detector has no unit tests.

### What I could NOT verify

- Whether the tests pass on this machine (pytest unavailable).
- The exact pass/fail/skip breakdown (HANDOFF says 58 / 3).
- Whether `test_each_attack_parses_fake_response` parametrizes across exactly 4 attacks (I read `attacks/__init__.py` which exports 4 patterns; consistent with the claim).
- Whether any test currently fails after the repo's recent reorganisation.

**Recommendation:** before paper submission, run `python -m venv venv && ./venv/bin/pip install -e .[dev] && ./venv/bin/pytest -q` on a fresh server and confirm 58 / 3.

---

## Pass 5 — Docs

### Files audited

| Path | Lines | `##` headings | Links |
|---|---:|---:|---:|
| `README.md` | 185 | 10 | 24 |
| `STATUS.md` | 133 | 7 | 1 |
| `HANDOFF.md` | 386 | 15 | 2 |
| `docs/REPRODUCIBILITY.md` | 171 | 10 | 3 |
| `docs/data_card.md` | 79 | 10 | 2 |
| `docs/disclosure_policy.md` | 23 | 0 | 1 |
| `docs/hf_dataset_card.md` | 199 | 11 | 3 |
| `docs/phase5_to_phase8_complete.md` | 52 | 3 | 0 |
| `docs/phase9_detector_evaluation.md` | 105 | 7 | 3 |
| `docs/phase10_ablations.md` | 170 | 9 | 6 |
| `docs/phase10i_atomic_monitor.md` | 199 | 7 | 1 |
| `docs/phase11_mathlib_case_study.md` | 56 | 4 | 0 |
| `docs/schema.md` | 54 | 3 | 0 |
| `docs/threat_model.md` | 147 | 8 | 0 |

(`docs/templates/disclosure_email.txt` is plaintext, not markdown — outside this pass.)

There is no `AGENTS.md` at the repo root.

### `## headings` per file

- **README.md** (10): Overview · Headline numbers · The four attack patterns · SpecGuard — companion defender · Reproduce · Pipeline at a glance · Repository layout · What you need to run this · Citation · License
- **STATUS.md** (7): TL;DR · Headline numbers · Methodology story (the iteration history that became the paper) · What's preserved for clone-and-resume · What is NOT in this repo · Key files · Remaining work (laptop only — no server required)
- **HANDOFF.md** (15): 0. Resume on another server · 1. What this benchmark is · 2. Taxonomy · 3. Previous work · 4. Methodology · 5. Results · 6. What we beat and what we tied · 7. Novelty · 8. Honest negative results · 9. File layout · 10. Reproduction recipes · 11. Pre-flight checklist · 12. What is intentionally NOT in this repo · 13. Cost / runtime summary · 14. The single sentence
- **REPRODUCIBILITY.md** (10): Prerequisites · Bedrock credentials · Verifiers · Restoring preserved datasets · Phase-by-phase index · Cost estimates · Runtime estimates · Key environment variables · Troubleshooting · Reproducibility checklist
- **data_card.md** (10): Dataset summary · Supported tasks · Languages · Dataset structure · Source data · Annotations · Considerations · Ethical considerations · Citation · License
- **disclosure_policy.md** (0): no `##` headings.
- **hf_dataset_card.md** (11): Threat model · Schema · Splits · Generation methodology · Statistics · Detector evaluation summary · Intended use · Not intended use · License · Citation · Changelog
- **phase5_to_phase8_complete.md** (3): Summary · What happened (the methodology story) · Pipeline status
- **phase9_detector_evaluation.md** (7): Per-detector metrics · Paired discrimination · Per-attack detection rate · Per-language detection rate · Cost vs F1 · Monitor cross-contamination · Phase 9 follow-up: axiom_audit detection-shape fix
- **phase10_ablations.md** (9): 10a Elicitor sweep · 10b Temperature · 10c Monitor count · 10d Ensemble grid · 10e Cross-language · 10f SSC baseline · 10g Adaptive attack · 10h Can SpecGuard beat SSC? · 10i Atomic-criteria monitor
- **phase10i_atomic_monitor.md** (7): TL;DR · Method · Results · Comparison table · Verdict · Artifacts · Reproduce
- **phase11_mathlib_case_study.md** (4): Headline · axiom_audit hits · monitor_consensus hits · Sampled source files
- **schema.md** (3): Fields · Admission criterion · Versioning
- **threat_model.md** (8): Setting · Adversary · Capabilities · Defender · Out of scope · Model selection rationale · Generation methodology · Admission filter

### Key numeric claims, with provenance and cross-checks

#### `README.md`
- L49 "**57.0%** overall (1024 / 1798); **Dafny+Lean 61.3%** (gate ≥50% cleared)" ✓ (verified in Pass 3).
- L50 "monitor_consensus **F1 = 0.871** (R 1.000, P 0.771, FPR 0.297)" ✓.
- L50 "axiom_audit **F1 = 0.492** after the multi-language + preamble fix (100% recall on implementation_leak)" ✓.
- L51 "Atomic-criteria monitor (Phase 10i) breaks the 0.871 ceiling: K = 2 of 4 → F1 0.967 (P 0.936, R 1.000, FPR 0.068; 5-fold CV F1 0.967 ± 0.005); C3-alone variant F1 0.975 at 2 calls/side" ✓.
- L51 "1 monitor = 3 …" (continuation of Phase 10c claim) — see HANDOFF cross-check below.
- L52 "100 honest Mathlib lemmas: axiom_audit 0/100, monitor_consensus 23/100" ✓.
- L54 "1024 admitted triples as parquet, paper-grade dataset card, CC BY 4.0" ✓ (matches hf_dataset_card v0.3.0 entry).
- L82-87 SpecGuard table has 6 rows: `vacuity / mutation_coverage / ghost_leakage / axiom_audit / monitor_consensus / atomic_monitor`. The "Admitted-1024" badge (L11) is the only count badge. README header text says "5 detectors" by implication of the SpecGuard section ordering, but the table itself includes the 6th `atomic_monitor` row (L87). **This will be cross-checked in Pass 8 #5 against HANDOFF L51 wording "5 detectors + a new atomic-criteria monitor".**
- L89 "Combined-risk AUC on Phase 9 = **0.793**, paired Δrisk **+0.440**" ✓.
- L175 "year = {2026}" (citation).

#### `STATUS.md`
- L3 "**Updated:** 2026-05-19" (one day before HEAD's mtime 2026-05-20). Minor — does not represent a numerical error, but is now off-by-one.
- L31-34 Phase 7, 9, 10, 11 headline strings — all match HANDOFF.
- L42-44 v1 sanity 0.13% (1/756) / v2 10% (1/10) / v3 10% (1/10) — matches sanity_v[123]_report.json (each at 1/10 = 10%, v1 at 1/756 from earlier mentioned in commit messages).
- L55-56 "Sanity progression: **10% → 50% → 50% → 60%**" — the v2/v3/v3-like reports are all 10%, and v4 report is 60%. The 50%/50% steps are between v2→v3→v3.5 generation runs that aren't represented as separate JSON files; reading suggests a non-monotone path that the report description glosses. Minor.
- L82 "**1 monitor = 3 monitors = 5 monitors** in F1 (all 0.900–0.901)" — actual JSON values are 0.9009 / 0.8996 / 0.8996. The displayed range "0.900–0.901" rounds 0.8996 up to 0.900 and 0.9009 up to 0.901 — defensible but loose. The phase10_ablations.md doc itself displays the per-panel F1 as 0.901 / 0.900 / 0.900 (3-dp).
- L88 atomic K=2-of-4: F1 0.967, FPR 0.068 ✓.

#### `HANDOFF.md`
- Front matter: L1 "Final Handoff (v0.2.0)", L4 "tag **`v0.2.0`** (commit `21cb74e`)", L385 "Tag: **`v0.2.0`** · Commit: **`21cb74e`** · Branch: `claude/professional-search-interface-MCp22`". **Repo HEAD is `76c0425`; `git tag` shows `v0.3.0`.** Stale version claim. **Flag for Pass 8.**
- §5 results table — every headline number verified against the corresponding JSON in Pass 3.
- §6 §7 §8 — narrative numbers match.

#### `docs/REPRODUCIBILITY.md`
- L168 "Phase 7 = 57.0%, Phase 9 monitor F1 = 0.871, axiom_audit fix → 100% recall on implementation_leak" ✓.
- L72/73 references `data/v1_backup_*.tar.gz` (1484+212) and `data/v4_backup_*.tar.gz` (1500+298). 1484+212 ≠ any number elsewhere in the repo; the 1500+298 matches phase5a/5b SUMMARYs. The 1484/212 are v1-era pre-pivot counts (commit message context).
- L88 "data/triples/**/*.json (1500)" + L89 "data/triples_xfamily/**/*.json (300)" — but in v4 it's 298, not 300 (Phase 5b yield = 99.3%). Minor inconsistency — README/STATUS use 1500+298 throughout.

#### `docs/data_card.md`
- No numeric claims beyond ePrint references and citation year.

#### `docs/hf_dataset_card.md`
- L114-117 per-language admission table: Dafny 319/600 53.2%, Lean 417/600 69.5%, Verus 288/598 48.2%, all 1024/1798 57.0% ✓.
- L123-126 per-attack: implementation_leak 377/450 83.8%, vacuity 348/450 77.3%, domain_restriction 187/450 41.6%, predicate_swap 112/448 25.0% ✓.
- L132 per-elicitor sonnet 906 (haiku/llama counts follow on subsequent lines).
- L144-149 detector summary table P/R/F1/FPR/cost: static_only (0.793/0.490/0.606/0.128/0), axiom_audit (0.742/0.368/0.492/0.128/0), SSC (0.771/1.000/0.871/0.297/2), monitor_consensus (0.771/1.000/0.871/0.297/3), atomic K=2-of-4 (0.936/1.000/0.967/0.068/4), atomic C3-alone (0.953/0.998/0.975/0.049/2) — all match JSON.
- L158 "5-fold CV on Phase 10i: F1 = 0.967 ± 0.005, K* = 2 on every fold." ✓.
- **L195-196 Changelog: "v0.3.0 (2026-05-20): initial public release — 1024 admitted triples, paired honest controls, paper-grade …"** — confirms v0.3.0 is current. **HANDOFF L1/L4/L385 are stale.**

#### `docs/phase5_to_phase8_complete.md`
- L7-12 v1 vs v4 table: Main 1484 / 1500, Ablation 212 / 298, Admission 0.13% / 57.0%, Dafny n/a / 319/600 (53.2%), Lean n/a / 417/600 (69.5%), Verus 0% / 288/598 (48.2%). ✓ all v4 numbers match.

#### `docs/phase9_detector_evaluation.md`
- L11-15 per-detector table (TP/FN/FP/TN/P/R/F1/FPR/cost) ✓ all match phase9_metrics_v2.json.
- L17 "Combined-risk AUC: **0.793**. Trojan mean risk **0.750**, honest mean risk **0.310**." — JSON has trojan 0.75, honest 0.3105. Rounded ✓.
- L29-33 paired-delta table ✓.
- L59-67 monitor cross-contamination — JSON has 9 cells with miss_rate {0, 0, 0, 0, 0, 0, 0.017, 0, 0.002}. Doc displays 0.002 for Llama→sonnet (2/906) and 0.017 for Llama→haiku (1/59). The third non-zero cell in the JSON is `bedrock-llama-70b.llama` which doc shows as 0. ✓.
- L89-96 "before/after" axiom_audit table: TP 0 → 377, FN 1024 → 647, FP 0 → 131, TN 1024 → 893, P 0 → 0.742, R 0 → 0.368, F1 0 → 0.492, FPR 0 → 0.128 ✓.
- L100 "Per-language rate (after, trojan side): Dafny 119/319 (37.3%), Lean 131/417 (31.4%), Verus 127/288 (44.1%)" — JSON per_language axiom_audit: dafny 119/319=0.373 ✓, lean 131/417=0.3141 ≈ 31.4% ✓, verus 127/288=0.4410 ≈ 44.1% ✓.

#### `docs/phase10_ablations.md`
- 10a L10-13 per-elicitor 5-detector F1 table — matches phase10_10a_elicitor_sweep.json bottom row (`per_detector.monitor_consensus.f1`) for each elicitor: all 0.871, sonnet 0.869 (JSON 0.8691), haiku 0.894 (JSON 0.8939), llama 0.874 (JSON 0.8741). ✓ rounded to 3 dp.
- 10b L24-27 temperature table — all 200/0/0/1.000/1.000 ✓.
- 10c L36-38 panel table — F1 0.901 / 0.900 / 0.900 (rounding of 0.9009 / 0.8996 / 0.8996). ✓.
- 10d L43 "Best by F1: monitor_consensus — F1 0.871 (P 0.771, R 1.000, FPR 0.297, cost 3 LLM calls/triple)" ✓.
- 10e L55-57 per-language F1 table — same triple repeated (in-language F1: dafny 0.995, lean 0.851, verus 0.677). Threshold 0.750 in all three. ✓.
- 10f L68-69 SSC and monitor_consensus rows ✓.
- 10g L75 57/60 (95.0%) ✓; L76 axiom_audit 0.316 ✓.
- 10h L91-95 H1-H5 table: H1 F1 0.606 cost 0; H2 R 1.000 F1 0.870; H3 SSC: Dafny 0.992, Lean 0.970, Verus 0.678; H3 monitor_consensus: Dafny 0.995, Lean 0.970, Verus 0.677; H4 LogReg F1 0.8705 ± 0.023; H5 F1 0.873. JSON cross-check: H1 F1 0.6059 ✓ rounded; H2 f1 0.8702 ✓ rounded; H4 0.8705 ✓; H5 0.873 ✓; H3 ssc.verus.f1=0.6784 (doc says 0.678 ✓); H3 monitor_consensus.verus.f1 not in 10h JSON but in 10e — phase10_10e_cross_language Verus in-lang F1 is 0.6769 (matches doc 0.677 ✓).
- 10i L149-152 K-of-4 sweep table P/R/F1/FPR ✓.

#### `docs/phase10i_atomic_monitor.md`
- L51-54 K-of-4 sweep table ✓.
- L71-77 5-fold CV table ✓ (mean test F1 0.9668, std 0.0049 → rounded display 0.967 ± 0.005).
- L86-88 per-language at K=2: Dafny 0.992, Lean 0.970, Verus 0.937 ✓.
- L99-102 per-attack at K=2: domain_restriction 0.982, predicate_swap 0.970, implementation_leak 0.964, vacuity 0.961 ✓.
- L111-114 per-criterion alone: C1 0.868, C2 0.562, C3 0.975, C4 0.934 ✓.
- L133-134 failure-count distribution (`atomic distribution table by failures 0/1/2/3/4`): honest 714/240/59/11/0, trojan 0/0/119/499/406. Cross-check: trojan sum = 1024 ✓; honest sum = 1024 ✓. At ≥2 failures: 70 honest (59+11+0=70) ✓ and 1024 trojans ✓.
- L116-117 "C3 logical_fidelity alone (F1 0.975) actually beats the combined K = 2-of-4 rule (F1 0.967). The combined rule wins on robustness" — accurate framing.
- L137 "100% of trojans fail ≥ 2 criteria" ✓ (1024/1024).
- L138 "95% of honest specs fail < 2 criteria" — (714+240)/1024 = 954/1024 = 0.9316 ≈ **93.2%**, not 95%. **Minor: doc says 95%, actual is 93.2%. Flag.**

#### `docs/phase11_mathlib_case_study.md`
- L3 "**100** Lean theorems" ✓.
- L9-10 axiom_audit 0/100 (0.000), monitor_consensus 23/100 (0.230) ✓.
- Lists 20 axiom_audit "hits" and 20 monitor_consensus "hits" (likely first-20-by-source-file ordering — not numerically checked).

#### `docs/schema.md` & `docs/threat_model.md`
- schema.md: no numeric claims (field-definition document).
- threat_model.md L73-78 mentions GPT-OSS-120B / DeepSeek-v4-Pro / Kimi-K2.6, with GLM family producing "1 admissible schema-conformant object in 2 of 3 multi-language sanity trials (1/3 yield, against 7/7 for the other three families)". This is generator-pivot evidence; numbers not present in JSON, only in commit-message history.
- threat_model.md L105-108 "300 triples from two additional Bedrock generators … 100 per language, 75 per attack pattern" — but phase5b_SUMMARY.json shows 298 admitted (yield 99.3%), 100/100/98 per language, 75/75/75/73 per attack. Doc says "300" and "75 per attack pattern"; actual is **298** total with predicate_swap at **73**. Minor 2-of-300 yield-shortfall not propagated into the threat-model prose. **Flag — small but consistent issue.**

### Phase-doc coverage cross-check (HANDOFF §5 vs `docs/`)

| Phase in HANDOFF §5 | Has dedicated doc? |
|---|---|
| 5a, 5b, 6, 7, 8 | `docs/phase5_to_phase8_complete.md` ✓ |
| 9 | `docs/phase9_detector_evaluation.md` ✓ |
| 10a–10h | `docs/phase10_ablations.md` (one doc covers all 8) ✓ |
| 10i | `docs/phase10i_atomic_monitor.md` (dedicated deep-dive) + section in `docs/phase10_ablations.md` ✓ |
| 11 | `docs/phase11_mathlib_case_study.md` ✓ |
| **12 (HF Space demo)** | **No `docs/phase12_*.md`.** Referenced only via `scripts/demo_gradio.py` + `hf_space_build/` and a one-liner in README/HANDOFF. **Missing doc.** |
| **13 (HF Dataset release)** | `docs/hf_dataset_card.md` ✓ (different naming, but functionally complete) |

### Pass-5 conclusions

- All major numeric claims in the docs trace to specific JSON values, with three exceptions to flag:
  1. **Version drift.** HANDOFF.md still says "v0.2.0 / commit 21cb74e", whereas `git tag` shows v0.3.0 and HF dataset card confirms v0.3.0 (2026-05-20). HANDOFF needs an update.
  2. **Rounding looseness on Phase 10c.** STATUS/HANDOFF write "0.900–0.901" but the underlying JSON values are 0.9009 / 0.8996 / 0.8996. Doc (`phase10_ablations.md`) is fine; STATUS/HANDOFF prose is the off-by-one-in-the-fourth-decimal-place case.
  3. **Phase 10i honest-fail-rate prose**. `phase10i_atomic_monitor.md` L138 says "95% of honest specs fail < 2 criteria" — actual is 93.2% (954/1024). Will flag in Pass 8.
- **Phase 12 has no dedicated doc.** This is mild but reportable.
- Phase 5b generator distribution (298 vs 300; per-attack 75 vs 73 for predicate_swap) is glossed in `threat_model.md` and `REPRODUCIBILITY.md` (300 / 75) but correctly stated in `phase5b_SUMMARY.json` (298 / 73).

---

## Pass 6 — Reproducibility surface

### `scripts/reproduce.sh` (112 lines)

**What it does.** Single-entrypoint reproducer with 9 banner-printed steps: (0) create venv + install package + run pytest + ruff; (1) check `.env`; (2) restore both backup tarballs into `data/triples/` and `data/triples_xfamily/`; (3) call `scripts/install_verifiers.sh`; (4) build the Lean+Mathlib template ($HOME/lean-project-template); (5) Phase 7 verifier re-check (skipped if `phase7_admission_report.json` exists); (6) Phase 9 SpecGuard (skipped if v2 jsonl exists); (7) Phase 10 post-hoc ablations (10a, 10d, 10e, 10h); (8) Phase 10i re-aggregation from committed JSONL; (9) prints instructions for the LLM-heavy batch.

**Flags**:
- **L6 hardcoded branch:** `git checkout claude/professional-search-interface-MCp22` — but the working tree is on `main` and the latest tag is `v0.3.0`. Documenting an obsolete branch in the example commands will confuse a reproducer.
- **L36 / L42 glob expansion:** `tar -xzf data/v1_backup_*.tar.gz` — shell glob, fine as long as exactly one match. With two tarballs present (the current case) `tar -xzf` with two args would unpack both, which is intended.
- **L91 silent failure:** `$PY scripts/10h_beat_ssc.py 2>/dev/null || echo "(10h needs ... skipping)"` — swallows the script's stderr entirely. If `10h` legitimately fails for a different reason on a fresh server, the reproducer will silently mark it skipped. Mild.
- **L74-85 Phase 9 branch**: the "else" branch (re-run from scratch) calls `scripts/_phase9_axiom_replay.py` after the initial eval, which is the post-fix replay step. A fresh-server reproduction will exercise this; otherwise it's skipped. OK.

### `scripts/install_verifiers.sh` (45 lines)

**What it does.** Idempotent installer for: system Z3 (apt), Dafny via dotnet tool, Lean 4 + Mathlib (via `elan`), and Verus (clone + `cargo build --release`).

**Flags**:
- **Sudo apt** (L7, L17): assumes Debian/Ubuntu with sudo. Not portable to other distros; fine for documented Linux setup.
- **No version pinning for Lean 4 / Verus**: `elan default leanprover/lean4:stable` and `git clone --depth 1 https://github.com/verus-lang/verus.git`. Will pull whatever is `stable` at run time, which may drift away from the v4 verifier-admitted benchmark. The HANDOFF says "Dafny 4.11, Lean 4 + Mathlib, Verus, Z3"; HANDOFF.md L48 also says "Lean 4.29". **No commit pin in `install_verifiers.sh` for Lean or Verus.** Reproducibility risk over time.
- **L20** `dotnet tool install -g dafny` — pulls the latest Dafny. Not version-pinned. (Cosmetic.)
- **L36** `[ ! -d "$HOME/verus" ]` — skip-if-present idempotency.
- No `set -e` after the initial line? Actually `set -euo pipefail` is at L4 — so any failure aborts. OK.

### `scripts/run_phase10_phase11.sh` (58 lines)

**What it does.** Sequentially runs the seven Bedrock-billed stages: 10b, 10c, 10f, 10g, 10h, 10i, 11. After each, calls a `gitci` helper that **stages, commits, and pushes to remote `origin/<branch>`.**

**Serious flags**:
- **L15** `BR=claude/professional-search-interface-MCp22` — **hardcoded branch that does not match the current branch (`main`).** Anyone reproducing on a fork or different branch will fail at the first `git push`.
- **L16-20 `gitci()`**: uses **`-c user.name="Mohammad Zeeshan" -c user.email="hdglit@inf.elte.hu" --author="Mohammad Zeeshan <hdglit@inf.elte.hu>"`** — hardcodes the original author's name and ELTE email into every commit. Anyone reproducing will mint commits attributed to Mohammad Zeeshan. **Two issues:** (a) it's incorrect attribution if a third party runs this; (b) it embeds a personal email into anyone's reproduction history. **Flag.**
- The script auto-commits + auto-pushes after each Bedrock-billed stage. The brief says "do NOT push, pull, or commit anything" — I did not run this script (and shouldn't); flagging that the script's design **is** push-on-success. For a public-release reproducer this is unusual; most projects let the user commit themselves.

### `pyproject.toml`

**What it declares.**
- `name = "trojanspec"`, **`version = "1.0.0"`**.
- `requires-python = ">=3.10"`.
- License: Apache-2.0.
- Author/maintainer: Mohammad Zeeshan / hdglit@inf.elte.hu.
- Dependencies: pydantic ≥2.6, httpx ≥0.27, python-dotenv ≥1.0, tqdm ≥4.66, numpy ≥1.26, scipy ≥1.12, pandas ≥2.2.
- Optional dependency groups: `viz` (matplotlib/seaborn/jupyter), `hf` (datasets/huggingface-hub), `review` (streamlit), `dev` (pytest, pytest-asyncio, ruff, mypy).
- Project URL: Homepage/Repository = `https://github.com/m-zest/trojanspec-bench`.
- `[project.scripts] trojanspec = "trojanspec.cli:main"` — CLI entry point.
- `[tool.pytest.ini_options]`: `testpaths = ["tests"]`, `asyncio_mode = "auto"`, `addopts = "-q --strict-markers"`, markers `verifier` + `network`.
- `[tool.ruff]`: `line-length = 100`, `target-version = "py310"`, src dirs `["src", "scripts", "tests"]`, **`ignore = ["E501"]`** (line-length check disabled). Selected rules: E F I B UP W C4.
- `[tool.mypy]`: `python_version = "3.10"`, files = `["src"]`.

**Flag: version drift.** Three version strings in one repo:
- `pyproject.toml` → **1.0.0**
- `HANDOFF.md` → **v0.2.0** (`21cb74e`)
- `git tag` → **v0.3.0**
- `docs/hf_dataset_card.md` changelog → **v0.3.0 (2026-05-20)**

No one of these three is "correct" without a release-notes blessing. The repo directory name is `TrojanSpec-Bench-v1.0` (consistent with `pyproject 1.0.0`), but the HF and tag artifacts say v0.3.0.

### `.env.example`

Variables declared (in order):
- `FIREWORKS_API_KEY=`
- `OPENROUTER_API_KEY=`
- `ANTHROPIC_API_KEY=`
- `OPENAI_API_KEY=`
- `OLLAMA_HOST=http://localhost:11434`
- `OLLAMA_MODEL=qwen2.5:32b`
- `HF_TOKEN=`

**MAJOR FLAG: `.env.example` declares no AWS variables.** Yet:
- `HANDOFF.md` L20-22 instructs the user to `cp .env.example .env && $EDITOR .env` and **set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_DEFAULT_REGION`** for Bedrock.
- `scripts/reproduce.sh` L26-30 checks for `AWS_ACCESS_KEY_ID` in the user's `.env` and prints "WARNING: AWS_ACCESS_KEY_ID empty — Bedrock calls will 401."
- `src/trojanspec/utils/llm_clients.py:282` calls `os.environ.get("AWS_DEFAULT_REGION", "us-east-1")`.
- All v4 admitted triples (1024) were generated through Bedrock cross-region inference profiles.

So the headline pipeline is **Bedrock-backed** but the `.env.example` template only lists Fireworks/OpenRouter/Anthropic/OpenAI/Ollama/HF — i.e., a template from the *pre-Bedrock-pivot* era. A fresh-server reproducer who edits the .env per the example template **will not have AWS_* keys set** and Bedrock will 401 until they add the variables manually after reading the warning. **This is the single most embarrassing reproducibility gap I found in this pass.**

The real `.env` file is NOT present (correctly gitignored).

### `.gitignore`

Verified the patterns the brief asked about:
- **`tmp*`** (L98) ✓ — explicitly added after the bdf082f Verus binary leak.
- **Tarball pattern** (L59) `data/*.tar.gz` ignored, with a `!data/v?_backup_*.tar.gz` un-ignore on L63 to allow the v1/v4 backups to be tracked. ✓
- **`venv/`** (L24) ✓; also `.venv/`, `env/`, `ENV/`.
- **`.env`** ignored (L31), with `!.env.example` un-ignore (L33). ✓
- **`__pycache__/`** ✓, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/` ✓.
- **`data/triples/**/*.json` ignored** (L53), with **`!data/triples/.gitkeep`** un-ignore (L67) and **`!data/**/*_SUMMARY.json`** (L68). This is exactly why the raw triple JSONs are absent from the working tree and the SUMMARY + .gitkeep are present — the "Raw triples are git-ignored (regenerated locally)" note in `phase5a_SUMMARY.json` is enforced by `.gitignore`.
- **`figures/*.png` ignored** (L72) with explicit phase9/10/11/12 re-allows (L75-78). ✓
- **`*.swp`, `*~`, `.DS_Store`, `Thumbs.db`** all ignored. ✓
- **No real `.env` present in the working tree** (verified by `ls -la`).

### Pass-6 conclusions

The most important reproducibility findings, in priority order:

1. **`.env.example` is missing AWS_* keys** but every headline-generating script depends on Bedrock. Fix by appending the three AWS variables to `.env.example` with empty values + a comment.
2. **`scripts/run_phase10_phase11.sh` hardcodes a personal author identity and a non-current branch** (`claude/professional-search-interface-MCp22`). Replace `gitci()` with either a no-op (preferred for a public reproducer) or a generic `git add -A && git commit -m "..."` without overriding author/email.
3. **Three different version strings**: `pyproject 1.0.0` / HANDOFF "v0.2.0" / tag `v0.3.0`. Reconcile to one.
4. **Lean/Verus toolchains not pinned** in `install_verifiers.sh` (uses `elan stable` + `git clone --depth 1`). Pin to the same commits the headline run used (HANDOFF says Lean 4.29).
5. **`reproduce.sh` checkout branch (L6) is stale** (`claude/professional-search-interface-MCp22`). Should reference `v0.3.0` tag or `main`.

---

## Pass 7 — Git hygiene

### `git status`

```
On branch main
Your branch is up to date with 'origin/main'.

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	AUDIT_REPORT.md

nothing added to commit but untracked files present (use "git add" to track)
```

The only untracked file is `AUDIT_REPORT.md` — the file I am writing right now. **No other untracked work.**

### `git log --oneline -30` (verbatim)

```
76c0425 Merge pull request #16 from m-zest
36948f6 docs: HF Space + HF Dataset badges and Phase 12/13 rows in README/STATUS/HANDOFF
180be3d phase13: HuggingFace dataset release with full README at m-zest/trojanspec-bench
019e6eb Merge pull request #15 from m-zest
4817614 phase12: Gradio demo + HF Spaces deployment at m-zest/specguard-demo
b4d86e8 Merge pull request #14 from m-zest
0c9d66a handoff: single-file resume guide + reproduce/run scripts extended for 10h/10i
93ec404 Merge pull request #13 from m-zest
21cb74e phase10i: atomic-criteria monitor breaks the 0.871 ceiling (F1 0.967)
23b97df Merge pull request #12 from m-zest
e785c1e phase10h: can SpecGuard beat SSC? (5 hypotheses tested, honest verdict)
ddb67c1 Merge pull request #11 from m-zest
2ed6a43 docs: STATUS + README updated with actual Phase 10/11 numbers
7cfd1cf phase10+11: consolidated docs/phase10_ablations.md + docs/phase11_mathlib_case_study.md
d91f4b7 phase11: Mathlib case study (100 sampled theorems, axiom_audit + monitor_consensus)
e4e0d14 phase10g: adaptive attack (banned-marker evasion, 60 impl_leak)
1e508e2 phase10f: SSC baseline (single-model 2-question consistency)
ffb8912 phase10c: monitor count ablation (1 vs 3 vs 5, 300 triples)
70e243c Merge pull request #10 from m-zest
c7a202d chore: ruff cleanup on phase 9-followup validation helpers (E401, I001, E702)
9d0de84 docs: STATUS.md rewrite (Phase 5 v4 / Phase 7-11 / handoff)
a38710e phase10+11: orchestrator now invokes _phase10_report.py and _phase11_report.py after 11
0ca607f phase10+11: consolidated report scripts (run after the orchestrator finishes)
8471e7c docs+repro: README rewrite + REPRODUCIBILITY guide + v4 dataset tarball
9b917a2 phase10b: monitor temperature ablation (200 triples x temps 0.0/0.3/0.7/1.0)
13b6570 phase10+11: harness for 10b/c/f/g monitor ablations + Phase 11 Mathlib case study
97c8164 Merge pull request #9 from m-zest
bb78be6 phase10d+e: detector ensemble grid + cross-language transfer
96156ef phase10a: elicitor sweep (Sonnet n=906 / Haiku n=59 / Llama n=59)
e35c763 phase9-followup: commit Phase 9 figures referenced in paper
```

Observations: every Phase 10 stage has its own commit, with one or two "Merge pull request #N from m-zest" merges (consistent with a single-author PR-based workflow). The Verus binary leak from `bdf082f` (mentioned in HANDOFF §12) is not in the last 30; that fix is in older history (the .gitignore `tmp*` entry is the post-fix evidence).

### `git tag`

```
v0.2.0   → 21cb74ee6341da1ad5fa92876c5dd6491d4cca46  (Mohammad Zeeshan <hdglit@inf.elte.hu>)
v0.3.0   → f07a50d533daa870ae147c45046460da4d8a06a0  (Mohammad Zeeshan <hdglit@inf.elte.hu>)
```

(Both tags annotated; the `git log` short SHA of v0.2.0 matches the `21cb74e` quoted in HANDOFF. The tag `v0.3.0` resolves to an annotated-tag object whose target is **`36948f6`**, the "docs: HF Space + HF Dataset badges" commit, which is the immediate parent of HEAD = `76c0425`.)

So the version landscape is:
- `v0.2.0` = `21cb74e` (Phase 10i commit, 9 commits behind HEAD)
- `v0.3.0` = `36948f6` (HF dataset/demo commit, parent of HEAD)
- `HEAD` = `76c0425` (Merge PR #16 into `main`; effectively a fast-forward-equivalent merge of `feat/bench` into `main`)

### `git ls-files | wc -l`

**180 tracked files.** Breakdown:
- `.py` files: 92
- `.md` files: 15
- `.json` files: 31
- files under `tests/`: 14

### `git ls-files --others --exclude-standard`

**`AUDIT_REPORT.md`** — only the report I am authoring. No stray scripts, no half-finished docs, no leaked credentials, no editor backups.

### `git diff --stat HEAD~5 HEAD`

```
 .gitignore                                         |    1 +
 HANDOFF.md                                         |  385 ++++++++
 README.md                                          |   12 +-
 STATUS.md                                          |   24 +-
 data/phase10_10h_beat_ssc.json                     |  262 +++++
 data/phase10_10i_atomic.json                       |  400 ++++++++
 data/phase10_10i_atomic_results.jsonl              | 1024 ++++++++++++++++++++
 docs/hf_dataset_card.md                            |  198 ++++
 docs/phase10_ablations.md                          |   90 ++
 docs/phase10i_atomic_monitor.md                    |  198 ++++
 figures/phase10_atomic_vs_ssc.png                  |  Bin 0 -> 107125 bytes
 figures/phase10_beat_ssc.png                       |  Bin 0 -> 44532 bytes
 hf_space_build/README.md                           |   76 ++
 hf_space_build/app.py                              |  334 +++++++
 hf_space_build/examples.json                       |   29 +
 hf_space_build/requirements.txt                    |    3 +
 hf_space_build/trojanspec/__init__.py              |    1 +
 hf_space_build/trojanspec/specguard/__init__.py    |   51 +
 hf_space_build/trojanspec/specguard/axiom_audit.py |  122 +++
 hf_space_build/trojanspec/specguard/base.py        |   83 ++
 hf_space_build/trojanspec/specguard/ghost_leakage.py | 66 ++
 hf_space_build/trojanspec/specguard/mutation_coverage.py | 65 ++
 hf_space_build/trojanspec/specguard/vacuity_detector.py  | 53 +
 scripts/10h_beat_ssc.py                            |  330 +++++++
 scripts/10i_atomic_monitor.py                      |  554 +++++++++++
 scripts/13_hf_dataset_release.py                   |  337 +++++++
 scripts/demo_gradio.py                             |  334 +++++++
 scripts/reproduce.sh                               |   17 +-
 scripts/run_phase10_phase11.sh                     |   17 +-
 29 files changed, 5057 insertions(+), 9 deletions(-)
```

Last 5 commits add Phase 10h/10i, the Gradio demo, the HF Spaces build dir, the HF dataset release script, the HANDOFF doc, badges/rows in README/STATUS/HANDOFF, and 2 figures. Net +5057 lines.

### Branches

- Local: only `main` (current).
- Remotes:
  - `origin/HEAD` → `origin/main` → `76c0425`
  - `origin/main` → `76c0425` (in sync with local main)
  - `origin/feat/bench` → `36948f6` (the v0.3.0-tagged commit; **this is a stale branch that has been merged into main via PR #16 and could be deleted**)

The HANDOFF reference branch `claude/professional-search-interface-MCp22` is **no longer present** on the remote — it has been replaced by `main` (origin/main) and `feat/bench`. **Anyone following HANDOFF L18 (`git checkout claude/professional-search-interface-MCp22`) will get a branch-not-found error.**

### Remote

```
origin  https://github.com/m-zest/TrojanSpec-Bench-v1.0.git (fetch)
origin  https://github.com/m-zest/TrojanSpec-Bench-v1.0.git (push)
```

Single remote; HTTPS; no SSH variant. ✓.

### Commit history sanity

- Total commits on HEAD: **85**.
- All recent commit messages are descriptive (phase-named, what changed in 1 line).
- No "wip" or "fix" commits in the last 30. No `[skip ci]` markers.
- Author identity on tags is `Mohammad Zeeshan <hdglit@inf.elte.hu>` (matches pyproject.toml + the hardcoded identity in `run_phase10_phase11.sh`).

### Pass-7 conclusions

- **The working tree is clean except for `AUDIT_REPORT.md` (which is intentional).** Nothing untracked that looks like it SHOULD be tracked.
- **Three stale branch references in committed prose** point at `claude/professional-search-interface-MCp22`, which no longer exists on origin: `HANDOFF.md` L18, L385; `scripts/reproduce.sh` L6; `scripts/run_phase10_phase11.sh` L15. Pass-8 will fold this into the consistency findings.
- **`origin/feat/bench` is a stale post-merge branch.** Not destructive, but a fresh `git fetch` user will see a "ghost branch" that duplicates `v0.3.0`. Optional cleanup.
- **HEAD is past `v0.3.0` by exactly one merge commit (`76c0425`).** The tip of main is `Merge pull request #16 from m-zest` with no further content beyond merging `feat/bench` (which is at `v0.3.0`). For paper-submission purposes you should either tag `76c0425` as a new release or accept that `v0.3.0` is the canonical release and HEAD is one-merge-ahead.
- HANDOFF's "v0.2.0 / commit 21cb74e" reference is **9 commits stale.** This was already counted in earlier passes; restating here so it's filed under Git hygiene as well.

---

## Pass 8 — Consistency checks (the important pass)

### 1) Headline numbers appearing in 2+ places — list of conflicts

| Claim | README.md | HANDOFF.md §5/§6 | docs/<phase>.md | JSON (source of truth) | Conflict? |
|---|---|---|---|---|---|
| Phase 7 admission % | 57.0% (1024/1798) (L49) | 57.0% (1024/1798) (L142) | 57.0% (phase5_to_phase8 L9, hf_dataset_card L117) | `phase7_admission_report.json.admission_pct = 57.0` | ✓ all match |
| Dafny+Lean gate | 61.3% (L49) | 61.3% (L142, L168) | (implicit) | (319+417)/1200 = 61.33% | ✓ |
| `monitor_consensus` F1 | 0.871 (L50, L86) | 0.871 (L129, L143) | 0.871 (phase9_eval L15, phase10_ablations L43/L69, phase10i L154) | `phase9_metrics_v2.json.per_detector.monitor_consensus.f1 = 0.8707` | ✓ all rounded from 0.8707 |
| `axiom_audit` F1 | 0.492 (L50, L85) | 0.492 (L128, L143, L167) | 0.492 (phase9_eval L14, phase10i L152) | `phase9_metrics_v2.json.per_detector.axiom_audit.f1 = 0.4922` | ✓ |
| Atomic K=2 F1 | 0.967 (L51, L87) | 0.967 (L130, L152, L163) | 0.967 (phase10i L8, L52; phase10_ablations L150; hf_dataset_card L148) | `phase10_10i_atomic.json.best_rule_full.f1 = 0.9669` | ✓ |
| Atomic K=2 P | 0.936 (L51, L87) | 0.936 (L130, L152) | 0.936 (phase10i L52; hf_dataset_card L148) | `0.936` (JSON exact) | ✓ |
| Atomic K=2 FPR | 0.068 (L51, L87) | 0.068 (L130, L152, L164) | 0.068 (phase10i L8; phase10_ablations L150; hf_dataset_card L148) | `0.0684` | ✓ |
| Atomic 5-fold CV F1 | 0.967 ± 0.005 (L51) | 0.967 ± 0.005 (L152) | 0.967 ± 0.005 (phase10i L12; hf_dataset_card L158; phase10_ablations L155) | `mean 0.9668 std 0.0049` | ✓ |
| C3-alone F1 | 0.975 (L51) | 0.975 (L165) | 0.975 (phase10i L113, L116; phase10_ablations L153) | `per_criterion_alone.logical_fidelity.f1 = 0.9752` | ✓ |
| SSC F1 | (not surfaced) | 0.871 (L149) | 0.871 (phase10_ablations L68; phase10i L153) | `phase10_10f_ssc_summary.json.f1 = 0.8707` | ✓ |
| SSC FPR | — | 0.297 (L149, L164) | 0.297 (phase10_ablations L68; phase10i L8, L153) | `0.2969` | ✓ |
| SSC FPR ratio over atomic | — | "4.4× lower" (L164) | "4.4×" (phase10i L10, L18) | 0.297 / 0.0684 = **4.342** | **Minor** — 4.4× is presented; computed ratio is 4.34×. Within rounding tolerance for narrative prose but **not** strictly "4.4× lower". |
| Phase 10c "1 = 3 = 5" range | "(continued)" (L51) | "0.900–0.901" (L146) | "0.901 / 0.900 / 0.900" (phase10_ablations L36-38) + STATUS L82 "0.900-0.901" | `phase10_10c_monitor_count.json` panels: 1→0.9009, 3→0.8996, 5→0.8996 | **Minor** — JSON min is **0.8996**, the prose lower bound 0.900 rounds it up. Doc-level 3-dp display is accurate. |
| Atomic "all 4 attack families ≥ 0.937" | — | "≥ 0.937" (L152) | "≥ 0.937" (phase10_ablations L157) | per-attack min = vacuity 0.9613 | **Cosmetic** — the threshold "0.937" looks lifted from the per-language Verus F1 (0.9366) by accident. The claim is technically true (0.961 ≥ 0.937) but the threshold is misnamed; the natural threshold for the per-attack table is ≥ 0.961. |
| Phase 11 Mathlib axiom_audit | "0/100" (L52) | "0/100" (L153) | "0/100 (0.000)" (phase11 L9) | `phase11_summary.json.axiom_audit_flagged = 0` | ✓ |
| Phase 11 Mathlib monitor_consensus | "23/100" (L52) | "23/100" (L153) | "23/100 (0.230)" (phase11 L10) | `phase11_summary.json.monitor_consensus_flagged = 23` | ✓ |
| Phase 10g axiom_audit recall on adaptive | — | "31.6%" (L150, L169) | "0.316" (phase10_ablations L76) | `phase10_10g_adaptive.json.axiom_audit_recall_on_adaptive = 0.3158` | ✓ rounded |
| Phase 10g 57/60 | — | "57/60 (95%)" (L150) | "57/60 (95.0%)" (phase10_ablations L75) | `admitted_after_reverify=57, sampled=60, admitted_pct=0.95` | ✓ |
| Phase 10h H4 LogReg | — | (referenced "all 5 hypotheses") (L151) | "5-fold CV F1 0.8705 ± 0.023" (phase10_ablations L94) | `phase10_10h.h4_logreg_ensemble.f1 = 0.8705, f1_std = 0.023` | ✓ |
| Phase 10i honest "< 2" fraction | — | — | "95% of honest specs fail < 2 criteria" (phase10i L138) | (714+240)/1024 = **954/1024 = 93.16%** | **Real inconsistency** — doc says 95%, actual is 93.16%. **Flag**. |
| Phase 5b total | 298 (README L48) | 298 (L142, L155) | 298 (phase5_to_phase8 L8, hf_dataset_card) | `phase5b_SUMMARY.json.generated = 298` | ✓ in headline docs |
| Phase 5b total | (still 298) | (still 298) | "300 triples" (`docs/threat_model.md` L105) + "data/triples_xfamily/**/*.json (300)" (`REPRODUCIBILITY.md` L89) | 298 | **Minor** — two ancillary docs say 300; the SUMMARY and headline docs say 298. |
| Phase 5b predicate_swap | — | — | "75 per attack pattern" (`docs/threat_model.md` L108) | 73 (`phase5b_SUMMARY.json.per_attack.predicate_swap = 73`) | **Minor** — same root cause as above. |
| Version | (no explicit version string) | "v0.2.0" / `21cb74e` (L1, L4, L385) | "v0.3.0" (`hf_dataset_card.md` L195) | `pyproject.toml.version = "1.0.0"`; `git tag` = v0.2.0, v0.3.0; HEAD = `76c0425` | **Major** — three different version strings. HANDOFF says v0.2.0 / 21cb74e (9 commits stale), HF dataset card and `git tag` agree on v0.3.0, pyproject.toml says 1.0.0. |

### 2) Phase 10i atomic_monitor verification

Brief asks to confirm each of: F1 0.967, 5-fold CV 0.967 ± 0.005, K* = 2 on every fold, FPR 0.068.

| HANDOFF claim | JSON value (`data/phase10_10i_atomic.json`) | Match? |
|---|---|---|
| F1 0.967 | `best_rule_full.f1 = 0.9669` | ✓ (rounds to 0.967) |
| 5-fold CV 0.967 ± 0.005 | `cv_rule_k.mean_test_f1 = 0.9668`, `std_test_f1 = 0.0049` | ✓ (mean rounds to 0.967, std rounds to 0.005) |
| K* = 2 on every fold | `cv_rule_k.folds[*].k_star_train` = **[2, 2, 2, 2, 2]** | ✓ exact |
| FPR 0.068 | `best_rule_full.fpr = 0.0684` | ✓ (rounds to 0.068) |
| Precision 0.936 | `best_rule_full.precision = 0.936` | ✓ exact |
| Recall 1.000 | `best_rule_full.recall = 1.0` | ✓ exact |

**All four checks pass to the precision claimed.** No deviation even in the 4th decimal place — the JSON already stores values rounded to 4 dp, and HANDOFF rounds further to 3 dp, but the rounding is consistent.

### 3) Phase 11 Mathlib verification

Brief asks: axiom_audit 0/100 (✓), monitor_consensus 23/100 (✓). **Does the file contain an `atomic_monitor` FPR on Mathlib?**

```
$ python3 -c "import json; print(list(json.load(open('data/phase11_summary.json')).keys()))"
['n_theorems', 'axiom_audit_flag_rate', 'axiom_audit_flagged', 'monitor_consensus_flag_rate', 'monitor_consensus_flagged', 'interpretation']
```

**No.** The file contains only `axiom_audit` and `monitor_consensus` rates. There is no `atomic_monitor_flag_rate`, `atomic_audit_*`, or per-criterion (C1..C4) rate on Mathlib. The `phase11_results.jsonl` first record confirms: each record carries only `{axiom_audit, monitor_consensus}` detector blocks.

**Confirmed gap.** The headline Phase 10i detector was never run against the honest-formal-mathematics calibration set. The paper can therefore claim (a) atomic K=2 F1 0.967 on the 1024 trojan set, (b) axiom_audit 0% FPR on 100 Mathlib lemmas, (c) coarse monitor_consensus 23% FPR on 100 Mathlib lemmas — but **cannot** claim an atomic-K=2 FPR on real formal mathematics. If a reviewer asks "how does the K=2 detector behave on real honest math?" the answer is "we did not run that experiment."

### 4) Phase 7 admission

Brief asks: 1024/1798 = 57.0%, Dafny+Lean 61.3%, plus per-language Dafny/Lean/Verus.

From `data/phase7_admission_report.json`:
- `admitted` 1024, `total` 1798, `admission_pct` 57.0 ✓
- `by_language.verus` 288/598 = **48.2%**
- `by_language.lean` 417/600 = **69.5%**
- `by_language.dafny` 319/600 = **53.2%**
- Dafny+Lean = (319+417) / (600+600) = 736/1200 = **61.33%** ✓ (matches "61.3%")
- `by_attack.implementation_leak` 377/450 = 83.8%
- `by_attack.domain_restriction` 187/450 = 41.6%
- `by_attack.vacuity` 348/450 = 77.3%
- `by_attack.predicate_swap` 112/448 = 25.0% — note the **denominator is 448 for predicate_swap**, not 450. So Phase 7 source set was 450·3 + 448 = 1798 triples total, with 2 predicate_swap drafts apparently missing from the Phase 5 generation pipeline. Consistent with phase5b yielding 298/300 instead of 300/300. **Not an error, just a structural detail to know.**
- `by_model` Sonnet 906/1500 (60.4%), Haiku 59/148 (39.9%), Llama 59/150 (39.3%).

### 5) Detector count — 5 vs 6

Brief: "README says 5 detectors, HANDOFF intro says 6. Which is correct?"

Canonical detectors in `src/trojanspec/specguard/`:
```
axiom_audit.py        — AxiomAuditDetector
ghost_leakage.py      — GhostLeakageDetector
monitor_consensus.py  — MonitorConsensusDetector
mutation_coverage.py  — MutationCoverageDetector
vacuity_detector.py   — VacuityDetector
```
(`base.py` defines `Verdict`, `DetectorResult`, `Detector` ABC, and `combined_risk`; `__init__.py` exports the registry. These are infrastructure, not detectors.)

**The canonical count is 5.** Both README and HANDOFF agree:
- README L42 "5 detectors, evaluated in Phase 9"; L77 "Five detectors"; L82-86 the table shows 5 baseline rows, then a 6th row `atomic_monitor (Phase 10i)` clearly labeled as the Phase 10i monitor.
- HANDOFF L50 "5 detectors + a new atomic-criteria monitor"; L121 "Phase 9, 5 detectors over the 1024+1024 set"; L179 "five detectors over `(preamble, original_spec, …)`"; L130 the table lists 6 rows, with the 6th explicitly labeled `atomic_monitor (Phase 10i)`.

The **brief's claim that HANDOFF intro says 6 is not exactly what HANDOFF says.** HANDOFF's framing is "5 baseline + 1 separately-developed atomic_monitor" (which lives in `scripts/`, not `src/trojanspec/specguard/`). README's framing matches. There is **no real inconsistency** on the 5-vs-6 question — both docs treat atomic_monitor as a Phase-10i experimental system rather than a 6th baseline detector.

### 6) Cross-attacker partition (GPT-5 / Gemini / non-Bedrock attacker)

Brief asks to search for any reference to GPT-5, Gemini, OpenAI, non-Bedrock attacker, or external-model attacker evaluation.

Result:
- **No references to GPT-5 or Gemini** anywhere in `src/`, `scripts/`, or any markdown doc.
- **OpenAI / GPT-4o references** are in `src/trojanspec/utils/llm_clients.py:495` (`"openai": (OpenAIClient, {"model": "gpt-4o"})` and `OpenRouterClient` fallback `"openai/gpt-4o"`), plus `.env.example` declares `OPENAI_API_KEY=`. These are configured LLM *backends*, not used by any trojan-generation phase in the v4 corpus.
- **`phase9_results_v2.jsonl`** elicitor distribution = `{us.anthropic.claude-sonnet-4-6: 906, us.anthropic.claude-haiku-4-5: 59, us.meta.llama3-3-70b: 59}` — **all three via Bedrock cross-region inference profiles**. Sum = 1024.
- The **cross-family** ablation (Phase 5b, the 298 set / 59 admitted Haiku + 59 admitted Llama) is *cross-family within Bedrock*, not cross-vendor.
- `docs/threat_model.md` L73-78 mentions that earlier sanity work with GPT-OSS-120B / DeepSeek-v4-Pro / Kimi-K2.6 (Fireworks-hosted) was abandoned (the "Phase 5 generator-quality pivot" mentioned in `llm_clients.py:452`).

**Confirmation: there is NO cross-attacker partition spanning multiple LLM vendors in the headline benchmark.** All 1024 admitted v4 triples were elicited via Bedrock. If the paper needs a cross-vendor attacker dimension, it does not exist in the current artifacts. **This is a real finding to flag.**

### 7) Per-attack-pattern counts in the actual triples

HANDOFF §2 claims: implementation_leak 377, vacuity 348, domain_restriction 187, predicate_swap 112 (sum = 1024).

Brief plan: "Verify by counting the actual tags across data/triples/ and data/triples_xfamily/."

As noted in Pass 1 and Pass 3, **the individual triple JSONs are NOT in the working tree** (they live in the v1/v4 tarballs, which `.gitignore` keeps unpacked-but-uncommitted). I substituted by counting the `attack_pattern` field across **every line of `data/phase9_results_v2.jsonl` (one record per admitted triple)** :

```
implementation_leak: 377
vacuity:             348
domain_restriction:  187
predicate_swap:      112
  TOTAL:            1024
```

**Exact match.** Also cross-verified against `data/phase7_admission_report.json.by_attack` (which reports the *admitted* count): same numbers. The Phase 10i atomic results JSONL also confirms via its own per-attack section (`per_attack_pattern_at_best_k.n_triples` = 377 / 348 / 187 / 112). Three independent files agree on this distribution. **No discrepancy.**

### 8) Other consistency notes surfaced incidentally

- **Stale branch references in committed prose**: `HANDOFF.md` L18, L385; `scripts/reproduce.sh` L6; `scripts/run_phase10_phase11.sh` L15 all say `claude/professional-search-interface-MCp22`. That branch is gone from `origin`. Reproducer instructions will fail.
- **`.env.example` missing AWS_* keys** but every documented reproduction step depends on them. Fresh-server reproducer will get a 401 on Bedrock.
- **`STATUS.md` "Updated: 2026-05-19"** — one day before the working-tree mtime 2026-05-20. Off by one.

### Pass-8 conclusions

- **All headline JSON-backed numbers** (Phase 7 admission, Phase 9 detectors, Phase 10a–i, Phase 11) verified against their source JSONs to the precision claimed.
- **Three minor numeric inconsistencies** worth fixing before the paper:
  1. `phase10i_atomic_monitor.md` L138 says "95% of honest specs fail < 2 criteria"; actual = 93.16%. (Cosmetic but reviewable.)
  2. HANDOFF/README's "4.4× FPR reduction" should be "4.34×" (or round to "4×"). 0.297 / 0.0684 = 4.342.
  3. `docs/threat_model.md` L105 / `docs/REPRODUCIBILITY.md` L89 say Phase 5b is "300 triples" / "75 per attack pattern"; actual is 298 / {75, 75, 75, **73**}.
- **One real factual gap**: Phase 11 Mathlib FPR is reported only for `axiom_audit` and `monitor_consensus`, not for the headline `atomic_monitor`. The paper cannot claim a "K=2 FPR on honest formal mathematics" from existing artifacts.
- **No cross-attacker (multi-vendor) partition** exists. All 1024 admitted v4 triples come from Bedrock-hosted Sonnet / Haiku / Llama. If a paper section relies on cross-vendor robustness, that section is unsupported by the current data.
- **The 5-vs-6 detectors question is a non-issue**; README and HANDOFF are consistent ("5 baseline + 1 separately-introduced atomic_monitor").
- **Version drift between pyproject (1.0.0) / HANDOFF (v0.2.0) / tag (v0.3.0)** is the most embarrassing surface-level inconsistency.

---

## Pass 9 — Risks and gaps

### Files that exist but appear unused

1. **`scripts/run_phaseA.sh`, `run_phaseA2.sh`, `run_phaseA3.sh`, `run_phaseA4.sh`, `run_phaseA4_regen.sh`** — Phase-7-era iteration scripts that produced `data/sanity_v{2,2b,3,4}_report.json`. None are called by `scripts/reproduce.sh` or `scripts/run_phase10_phase11.sh`, and none are mentioned in HANDOFF / README. The only doc reference is `docs/REPRODUCIBILITY.md` L103 which mentions `run_phaseA4_parallel.sh` as "Phase 7 (parallel resume, gate ≥50%, final report)" — but not the other five.
2. **`data/sanity_v2_report.json`, `v2b`, `v3`, `v4`** — committed by the run_phaseA*.sh scripts; not referenced by any post-Phase-5 narrative. Useful only as iteration-history evidence.
3. **`scripts/_diag_implleak.py`, `_val_implleak_shapes.py`, `_val_lean_fewshot.py`, `_val_lean_leak_repair.py`** — one-shot diagnostic/validation scripts from the v4 schema iteration. Not in any reproducer pipeline. They are documentation-only: STATUS.md alludes to "verifier-proven Lean few-shot rewrites" but doesn't name the validation script.
4. **`scripts/_phase_final_report.py`** (writes `docs/phase5_to_phase8_complete.md`) — referenced nowhere in pipelines; the doc it writes is committed, so the script is effectively a one-shot generator.
5. **`scripts/run_phase5.sh`** — referenced only in `docs/REPRODUCIBILITY.md` table L88-89 (as the Phase 5a/5b script); not called by `reproduce.sh`.
6. **`scripts/run_phase9.sh`** — similar: doc-referenced (REPRODUCIBILITY L104), not pipeline-invoked.
7. **`notebooks/` directory** — contains only `.gitkeep`. Either reserved for future notebooks or vestigial. README/HANDOFF do not promise any notebooks.
8. **`figures/.gitkeep`** — vestigial; the figures directory is non-empty.
9. **`TrojanSpec-Bench vs SPS-Control_ Strategic Analysis for the Secure Program Synthesis Hackathon.pdf`** (829 KB) — committed to repo root. Not referenced from any README / HANDOFF / doc. Strategic analyses are usually private; consider moving to a `docs/private/` (gitignored) or deleting from the public repo before paper submission.

### Functions/classes defined but never called

I did not run a static call-graph analysis (would require importing every module without side effects). Spot checks:

- **`LLMClient` base class** in `src/trojanspec/utils/llm_clients.py` has many configured family entries (`fireworks-*`, `openrouter-*`, `ollama-*`, `anthropic`, `openai`) that the headline v4 pipeline never uses (all v4 admitted triples are Bedrock-generated). The non-Bedrock family entries are configured but their usage in the headline corpus is zero. Pruning them would simplify the docs and the `.env.example` story.
- **`scripts/03_review_triples.py`** is a Streamlit page (Phase 6 review) — never invoked by `reproduce.sh` (the v4 admission is automated, not human-reviewed). It is documented as a developer tool. If Phase 6 is no longer in the pipeline narrative, this script could be archived.

### Phases mentioned in HANDOFF that lack a script OR data file

- **Phase 8** — HANDOFF §9 file layout doesn't list a Phase 8 script. `docs/phase5_to_phase8_complete.md` mentions "Phase 8: SpecGuard CLI (5 detectors) complete, tests passing" — i.e., Phase 8 is the **integration of SpecGuard into the CLI**, not a separately-orchestrated experiment. There is `scripts/05_specguard.py` (the SpecGuard CLI) but no `scripts/08_*.py`. The numbering jumps 5 → 9. Not a gap; just confusing.
- **Phase 12 (HF Space demo)** — has `scripts/demo_gradio.py` + `hf_space_build/` but no `data/phase12_*.json` and no `docs/phase12_*.md`. The demo is a deployed artefact; results would be hard to record as a JSON.
- **Phase 13 (HF Dataset release)** — has `scripts/13_hf_dataset_release.py` + `docs/hf_dataset_card.md`. No `data/phase13_*.json` artifact (release-side observability), but that's reasonable for a one-shot publish.

### Numbers in README/HANDOFF that I could NOT verify from the JSON

Three (already flagged):
1. HANDOFF/README "**4.4× FPR reduction**". Computed value: 0.297 / 0.0684 = **4.342×**. Within rounding tolerance for a narrative but strictly should be "**~4.3×**" or "**4×**".
2. STATUS L82 / HANDOFF L146 "**all 0.900–0.901**" for Phase 10c. JSON minimum is **0.8996**. Doc displays "0.901 / 0.900 / 0.900" (rounded), which is fine; the **lower-bound** claim in narrative prose silently rounds 0.8996 up to 0.900. Not a strict numerical match.
3. `docs/phase10i_atomic_monitor.md` L138 "**95% of honest specs fail < 2 criteria**". Computed value: (714+240+0)/1024 = **93.16%**. **Real off-by-2-pp error in the prose.**

### Dead branches in git

- `origin/feat/bench` (`36948f6`, the v0.3.0 commit) — already merged into `main` via PR #16. Stale post-merge branch.
- The branch named in HANDOFF, reproduce.sh, and run_phase10_phase11.sh — `claude/professional-search-interface-MCp22` — **no longer exists on origin**. Any reproducer following the published commands will hit `error: pathspec 'claude/professional-search-interface-MCp22' did not match any file(s) known to git`. **Real bug in the documented reproduction recipe.**

### Things that would embarrass a reviewer

1. **`.env.example` does not declare `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_DEFAULT_REGION`,** but the entire Bedrock-billed pipeline depends on them and `scripts/reproduce.sh` warns about them. A reviewer copying `.env.example` → `.env` per HANDOFF L21-22 will find their `.env` file lacks the very keys they're told to set.
2. **`scripts/run_phase10_phase11.sh` hardcodes the author's name and ELTE email and pushes to a branch that doesn't exist on remote**. A third-party reproducer running this script will (a) be branded `Mohammad Zeeshan <hdglit@inf.elte.hu>` in their own commits, (b) hit a push failure on the non-existent branch. Both are visible in the diff and look careless.
3. **Three different version strings in one repo** (`pyproject 1.0.0`, HANDOFF `v0.2.0/21cb74e`, tag `v0.3.0`). Reviewer pulling the repo per HANDOFF will find themselves at `v0.2.0` (9 commits behind HEAD) and wonder which numbers are which.
4. **The 829 KB PDF "TrojanSpec-Bench vs SPS-Control_ Strategic Analysis ..."** committed at the root. It mentions a "Hackathon" — looks like an internal positioning document. Possibly fine, but possibly intended to be private.
5. **HANDOFF §11 pre-flight checklist** says `assert abs(m['best_rule_full']['f1'] - 0.967) < 1e-3`. The actual value `0.9669` passes this check (`|0.9669 - 0.967| = 0.0001 < 0.001`). ✓ — no concern, just noting.
6. **Phase 11 Mathlib does not run the headline atomic_monitor.** A reviewer asking "what is the K=2 detector's FPR on real Mathlib?" gets no answer from the artifacts.
7. **`scripts/10i_atomic_monitor.py` (555 lines) lives in `scripts/`, not as a library module under `src/trojanspec/specguard/atomic_monitor.py`.** Consequences: (a) `hf_space_build/` can't `import` it; (b) no `pytest` unit tests cover it; (c) downstream users can't reuse the detector via the published `trojanspec` package. The headline detector is, formally, **scripts/ scaffolding**, not part of the published library API.
8. **`hf_space_build/trojanspec/specguard/` ships only 4 detectors** (no `monitor_consensus.py`). The Space therefore advertises "SpecGuard" but only runs `vacuity / mutation_coverage / ghost_leakage / axiom_audit` plus an inline atomic_monitor. A reviewer comparing the HF Space code to the main library will notice the asymmetry.
9. **`origin/feat/bench` post-merge branch** still present; minor.
10. **No release notes file** (`CHANGELOG.md`) to disambiguate v0.2.0 → v0.3.0 → HEAD. The HF dataset card has a 2-line changelog at L195-196 but the repo itself does not.

### CI workflows

- `.github/workflows/ci.yml` (37 lines): lint + type-check + tests on `push` (any branch) and `pull_request`. Python 3.11 only — but `pyproject.toml` declares support for 3.10 / 3.11 / 3.12. No matrix. Not a bug; missing matrix coverage.
- `.github/workflows/verifier-tests.yml` (31 lines): nightly cron at 03:00 UTC, runs `scripts/install_verifiers.sh` + a "sampled witness validation". Reasonable.

### Pass-9 risk register (in priority order)

| # | Risk | Severity | Fix effort |
|---:|---|---|---|
| 1 | `.env.example` missing AWS_* keys; reproducers will 401 on Bedrock | **High** | trivial — 3 lines |
| 2 | HANDOFF / reproduce.sh / run_phase10_phase11.sh point at non-existent branch `claude/professional-search-interface-MCp22` | **High** | low — 4 places to update |
| 3 | Phase 11 Mathlib doesn't include the headline atomic_monitor FPR | **High** | medium — needs ~100 Bedrock × 4 atomic calls (~ $0.30) |
| 4 | Atomic_monitor isn't a `src/trojanspec/specguard/` module; no unit tests | **Medium** | medium — refactor + tests |
| 5 | Version drift (pyproject 1.0.0 vs tag v0.3.0 vs HANDOFF v0.2.0) | **Medium** | low — reconcile to a single number |
| 6 | `run_phase10_phase11.sh` hardcodes personal author + pushes on every step | **Medium** | low — strip `-c user.name=… --author=…` and remove the push lines |
| 7 | `docs/phase10i_atomic_monitor.md` L138 prose says 95%, actual 93.16% | Low | trivial |
| 8 | "4.4× FPR reduction" is actually 4.34× | Low | trivial wording fix |
| 9 | `docs/threat_model.md` / `REPRODUCIBILITY.md` say Phase 5b is "300 / 75-each-attack" but SUMMARY says 298 / 73-predicate-swap | Low | trivial |
| 10 | Strategic-analysis PDF committed at repo root | Low | decide: keep, move, or delete |
| 11 | 6 historical `run_phaseA*.sh` scripts unused by reproducer | Low | optional — keep as iteration history or move to `scripts/legacy/` |
| 12 | `notebooks/` dir vestigial | Trivial | delete the dir or add a notebook |
| 13 | `figures/.gitkeep` vestigial | Trivial | delete |
| 14 | `origin/feat/bench` post-merge branch stale | Trivial | `git push origin --delete feat/bench` |
| 15 | `hf_space_build/specguard/` ships 4 detectors, main library ships 5 — visible asymmetry | Low | optional — document the why |
| 16 | No cross-vendor (non-Bedrock) attacker in v4 | Medium (scope) | NOT fixable in this release — paper must scope-down its robustness claims |

