# TrojanSpec-Bench — Status & Handoff (server-deletion snapshot)

**Updated:** 2026-05-18
**Branch:** `claude/professional-search-interface-MCp22` (HEAD pushed; remote synced)
**Reproduce:** `bash scripts/reproduce.sh` after cloning (read this file first).

---

## TL;DR

The library, generators, 3 verifier wrappers, 13/15 crypto anchors, SpecGuard
(5 detectors), and the full Fireworks→Ollama generation pipeline are built,
tested (`pytest` 55 passed / 1 skipped, ruff clean) and committed/pushed.

**Open problem:** end-to-end *admission* (a triple where a real verifier
accepts trojan_spec+witness AND rejects original_spec+witness) is stuck at
**~10%** on a 10-triple sanity. Three triple-contract iterations each fixed a
real structural bug surfaced by automated validation; the residual ceiling is
now **generator quality** (local Qwen-2.5-32B is not strong enough at formal
Dafny/Lean) plus **Verus uninstallable** here. No full 1500/300 regen has
been admitted yet. This iteration history *is* the paper's methodology story.

---

## What is DONE (committed & pushed)

| Area | State |
| :-- | :-- |
| Fireworks backend (4 families) then pivot to **local Ollama** (Qwen-2.5-32B primary; Qwen-Coder + DeepSeek-Coder ablation) | done |
| 13 crypto-primitive families, 15 anchors, 5/5/5 Dafny/Lean/Verus, no fabricated finding numbers | done |
| Generation script: weighted families, concurrency, retry/backoff, resume top-up, `--sanity`, `--xfamily` | done |
| Phase 6 Streamlit review UI | done (now bypassed — Phase 7 is sole filter) |
| Phase 7 auto-validator (sole admission filter, `reviewed_by="auto-phase7-validator"`, `validation_failed`/`schema_mismatch` flags) | done |
| Phase 8 **SpecGuard**: 5 detectors (vacuity, mutation-coverage, ghost-leakage, axiom-audit, monitor-consensus) + CLI `scripts/05_specguard.py` + 22 unit tests | done |
| Verifiers installed here: **Z3 4.8.12, Dafny 4.11, Lean 4.29 (+Mathlib template)**. **Verus failed to build** | partial |
| v1 dataset preserved: `data/triples_v1` (1484) + `data/triples_xfamily_v1` (212) + **committed tarball** `data/v1_backup_*.tar.gz` | done |

## The three triple-contract iterations (the methodology story)

| Ver | Contract | Bug it exposed (via automated validation) | Admission |
| :-- | :-- | :-- | :-- |
| **v1** | trojan_spec & trojan_witness each a full standalone program | concatenation duplicate-declares the symbol → never compiles | 0.13 % (1/756) |
| **v2** | single signature; spec = header only, witness = body | `compose()` brace-finding broke on set literals / `{:axiom}` / `verus!`; and Lean original_spec was a *different declaration* than the trojan | 10 % (1/10) |
| **v3** | shared **preamble** (helpers) + single target spec/witness | preamble fixed all `schema_mismatch`; **0/20 source-audit drops**. Residual failures are now genuine: Verus absent (3/10) and Qwen-generated Dafny/Lean where trojan+witness do not form a verifier-confirmed contradiction (`accepts_trojan=True, rejects_original=False`, or witness fails to verify) | 10 % (1/10) |

Each gate (sanity ≥70→40 %, source-audit 0 % drop, Phase-7 ≥50 %) fired
correctly and prevented wasting hours regenerating broken triples.

## The OPEN ISSUE (what's left)

v3 is structurally correct (zero schema_mismatch, audit passes, all unit
tests pass). The ~10 % ceiling is **not a pipeline bug** — it is:
1. **Verus uninstallable** in this environment → ~1/3 of every batch auto-fails (documented; raw-only release).
2. **Generator quality**: `qwen2.5:32b` (used because the 40 GB A100 cannot fit Qwen-72B, and Fireworks Tier-1 rate-limited) frequently emits Dafny/Lean where the trojan and witness do not form a real verifier contradiction. The `255f8177`/`51b44bd4`-style admits show the design works when the model gets it right.

**To raise admission, the next lever is the generator, not the schema:** a
stronger model (Fireworks/OpenRouter `gpt-oss-120b` or Qwen-72B on an 80 GB
GPU), or attack-prompt hardening (Cause C/D/E from the prior plan, not yet
applied because the user deferred them as "acceptable noise").

## Reproduce on any fresh server

```bash
git clone https://github.com/m-zest/TrojanSpec-Bench-v1.0.git
cd TrojanSpec-Bench-v1.0 && git checkout claude/professional-search-interface-MCp22
bash scripts/reproduce.sh        # venv, Ollama, models, verifiers, Lean/Mathlib, restore v1
bash scripts/run_phaseA3.sh      # sanity-gated full pipeline; tail -f /tmp/phaseA3.log
```
- Backend: **local Ollama, no API key needed** (`.env` only needed for the
  optional Fireworks fallback).
- v1 dataset auto-restored from the committed tarball
  (`tar -xzf data/v1_backup_*.tar.gz`).
- Orchestrators: `scripts/run_phaseA3.sh` (current, v3, gate 40 %),
  `scripts/run_phaseA2.sh`, `scripts/run_phaseA.sh` (history).
- Markers in the log: `SANITY_V3B_ADMISSION`, `PHASE7_DAFNY_LEAN_ADMISSION`,
  `PHASEA3_STOPPED_SANITY|STOPPED_PHASE7|SUCCESS|DONE`.

## Key files

- `src/trojanspec/schemas.py` — `Triple` (+ `preamble`, `triple_format_version`, `schema_mismatch`, `validation_failed`)
- `src/trojanspec/verifiers/compose.py` — v3 `compose(preamble, contract, witness, lang)`
- `src/trojanspec/generators/validator.py` — Phase 7; `_target_decl_name` (last decl)
- `src/trojanspec/crypto/*.py` — 15 anchors; 8 use `honest_preamble`
- `src/trojanspec/specguard/` — 5 detectors; CLI `scripts/05_specguard.py`
- `scripts/02_generate_triples.py` — generation; `scripts/04_validate_witnesses.py` — Phase 7
- `docs/threat_model.md` — model selection, generation methodology, admission filter, Verus deferral

## NOT started (per scope)
Phase 9 (evaluation), 10 (ablations), 11 (Mathlib case study), 12 (web demo),
13 (HF release), 15 (papers). Phase 6 human review intentionally bypassed.
