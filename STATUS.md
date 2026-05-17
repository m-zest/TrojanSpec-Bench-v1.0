# TrojanSpec-Bench — Session Status & Handoff

**Last updated:** 2026-05-17
**Branch:** `claude/professional-search-interface-MCp22`
**Remote:** `https://github.com/m-zest/TrojanSpec-Bench-v1.0.git`

This file is the single source of truth for resuming work. Read it top to
bottom after cloning.

---

## 1. What this project is

TrojanSpec-Bench studies adversarially elicited formal specifications: specs
that pass a verifier and read correctly in English but silently admit a buggy
implementation. Each item is a triple `(nl_requirement, original_spec,
trojan_spec, trojan_witness)`. A triple is *admitted* only when a real
verifier accepts `trojan_spec + trojan_witness` and rejects
`original_spec + trojan_witness`.

---

## 2. What has been done (this session)

Phases 0-4 (schemas, attack generators, verifier wrappers, crypto anchors)
were already present. This session delivered:

| Commit | Meaning |
| :-- | :-- |
| `ad926b2` | Fireworks added as primary LLM backend (4 model families) |
| `45eaded` | Crypto anchors expanded toward 13 primitive families |
| `7b96ec4` | Generation script: retry + concurrency control |
| `52a716a` | Anchors rebalanced **5 Dafny / 5 Lean / 5 Verus**, attack mix 4 vacuity / 4 leak / 4 domain / 3 swap, **all fabricated finding numbers removed** |
| `0d9229d` | Probe-based tuning (per-family token budgets, 300s timeout), hardened JSON extractor, **Phase 6 Streamlit review UI** |
| `eb52975` | GLM dropped from elicitor pool (unparseable output), 3-family |
| `5202065` | Weights 50/25/25, JSON-discipline prompt, witness-format rule, **gpt-oss structured output** |
| `cc64157` | Phase 5a config: **gpt-oss-only** for reliability (evidence-based); parameterized `--out-dir`/`--families`; summary helper |
| `9c9d961` | Phase 7 is the **sole admission filter** (no human review) — threat_model.md |
| `61450a5` | `validation_failed` schema flag + rewritten `scripts/04_validate_witnesses.py` (validates both data trees, auto-stamps `reviewed_by="auto-phase7-validator"`) |

All commits authored `Mohammad Zeeshan <hdglit@inf.elte.hu>`, pushed to the
branch above. `pytest tests/ -q` is green (26 passed, 1 skipped); `ruff`
clean.

**Crypto anchors:** 15 registered, covering all 13 primitive families,
5/5/5 across Dafny/Lean/Verus, no fabricated IACR finding numbers.

**Pipeline decisions locked in:**
- Generation: **gpt-oss-120b only** (sanity v2-v4 evidence: gpt-oss 12/12;
  deepseek ~65% + malformed specs; kimi ~40% + slow; GLM 1/3).
- Phase 5b cross-family ablation: 300 triples, deepseek+kimi 50/50, written
  to a **separate** `data/triples_xfamily/` tree.
- **No human review (Phase 6 skipped).** Phase 7 verifier validation is the
  only admission filter.

---

## 3. THE BLOCKER — Fireworks rate limit

The full 1,500-triple run (`scripts/run_phase5.sh`) was started and **failed
at 90/1,500**. Diagnosis:

| Check | Result |
| :-- | :-- |
| Failure code | **946/946 HTTP 429 `RATE_LIMIT_EXCEEDED`** (not auth/outage/5xx) |
| Single isolated call | Also **429** in 0.13s when the window is saturated |
| Account/usage API | No endpoint (404); balance only in Fireworks dashboard |
| 3 parallel calls | 2 × 200, 1 × 429 → capacity is low, not zero |
| Rate-limit headers | **None** (`x-ratelimit-*`, `Retry-After` absent) |
| Other models | deepseek/kimi/glm also 429 → **limit is account-wide** |

**Root cause:** the Fireworks API key is on a **very low account-wide
requests-per-minute tier** (single-digit RPM). A 1,500-job burst at
concurrency 8 swamped it. Switching model does not help (account-wide);
waiting does not help (persistent cap, not an outage).

**Options:**
- **(a)** concurrency 8→1-2 **+** client-side throttle **+** longer backoff,
  and likely cut the target to ~300-500. Runs in hours, fragile.
- **(b)** switch model — ruled out (account-wide limit).
- **(c)** wait — ruled out (persistent cap, not an outage).
- **(d)** switch backend (OpenRouter / Together / Anthropic) — needs a key
  the user supplies; gpt-oss structured-output path is Fireworks-specific.
- **Best:** upgrade the Fireworks plan / use a key with real RPM, then
  resume **unchanged** at concurrency 8. This is a billing action only the
  project owner can take.

**Decision required from the project owner before generation can proceed.**

---

## 4. How to resume after `git clone`

```bash
git clone https://github.com/m-zest/TrojanSpec-Bench-v1.0.git
cd TrojanSpec-Bench-v1.0
git checkout claude/professional-search-interface-MCp22

python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev,review]"
pytest tests/ -q                       # expect 26 passed, 1 skipped

cp .env.example .env
# Edit .env: set FIREWORKS_API_KEY=<a key with adequate RPM>  (NEVER commit .env)

# Smoke test the backend (10 triples, multi-language):
python scripts/02_generate_triples.py --sanity --concurrency 8
```

Then, once the rate-limit decision is made:

```bash
# Phase 5a + 5b chained (the runner that failed on the low-RPM key):
bash scripts/run_phase5.sh            # logs: /tmp/main1500.log, /tmp/xfamily300.log
#   5a -> data/triples/        (1500, gpt-oss only)
#   5b -> data/triples_xfamily/ (300, deepseek+kimi 50/50)

# Phase 7 (sole admission filter) — needs verifiers installed first:
bash scripts/install_verifiers.sh     # Dafny / Lean / Verus / Z3 (heavy)
python scripts/04_validate_witnesses.py
#   validates BOTH data trees; admitted -> reviewed_by="auto-phase7-validator"
#   failed -> validation_failed=true (kept for transparency)

# Phase 8: SpecGuard CLI (5 detectors) — NOT yet built (next task).
```

If the low-RPM key must be used, edit
`scripts/02_generate_triples.py` (`CONCURRENCY = 1`), raise
`_MAX_RETRIES`/`_BASE_DELAY_SEC` in
`src/trojanspec/utils/llm_clients.py`, and reduce `--per-cell`.

---

## 5. Local-only artifacts (NOT in git, regenerated)

- `.env` — contains the Fireworks key; git-ignored by design, never pushed.
- `data/triples/` — 90 partial gpt-oss triples from the failed run
  (git-ignored; regenerated by Phase 5a). Valid but incomplete; discard.
- `data/triples_xfamily/` — empty (5b never ran).
- Raw triple JSONs are git-ignored on purpose; per-phase
  `*_SUMMARY.json` manifests are the committed record (none yet — the run
  did not reach the summary step).

---

## 6. Next steps (in order)

1. **Owner decision** on the Fireworks rate limit (Section 3).
2. Resume Phase 5a (+5b) generation once unblocked.
3. `scripts/install_verifiers.sh`, then Phase 7 validation.
4. **Build Phase 8 — SpecGuard CLI (5 detectors)** — not started.
5. Report admission rates per language/attack/model; total cost.

Phases 9-17 (eval harness, ablations, Mathlib case study, web demo, HF
release, papers) remain unstarted per the original build spec.
