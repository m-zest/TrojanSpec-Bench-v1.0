#!/usr/bin/env bash
# Reproduce TrojanSpec-Bench end-to-end on a fresh machine.
#
# Quickstart:
#   git clone <repo> && cd TrojanSpec-Bench-v1.0
#   git checkout v0.4.0   # or: git checkout main
#   cp .env.example .env && $EDITOR .env       # set AWS_* for Bedrock
#   bash scripts/reproduce.sh                  # idempotent; resumable
#
# Steps are banner-printed and idempotent. Read docs/REPRODUCIBILITY.md
# first (env vars, costs, expected runtimes, troubleshooting).
set -uo pipefail
cd "$(dirname "$0")/.."
PY=./venv/bin/python
say(){ echo; echo "######## $* ########"; }

say "0. Python venv + package (idempotent)"
[ -d venv ] || python3 -m venv venv
./venv/bin/pip -q install --upgrade pip wheel
./venv/bin/pip -q install -e ".[dev]" matplotlib
$PY -m pytest -q tests/ || { echo "tests failed; aborting"; exit 1; }
./venv/bin/ruff check src/ tests/ scripts/ || echo "(ruff warnings - non-fatal)"

say "1. .env / Bedrock credentials"
[ -f .env ] || cp .env.example .env
if grep -qE '^AWS_ACCESS_KEY_ID=.+' .env; then
  echo "(.env has AWS_ACCESS_KEY_ID populated)"
else
  echo "WARNING: AWS_ACCESS_KEY_ID empty - Bedrock calls will 401."
  echo "Edit .env: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_DEFAULT_REGION."
fi

say "2. Restore preserved dataset tarballs (v1 + v4 admitted triples)"
if ls data/v1_backup_*.tar.gz >/dev/null 2>&1; then
  if [ -d data/triples_v1 ]; then echo "(v1 already restored)"
  else tar -xzf data/v1_backup_*.tar.gz; fi
else echo "(no v1 tarball)"; fi
if ls data/v4_backup_*.tar.gz >/dev/null 2>&1; then
  if [ -d data/triples ] && [ "$(find data/triples -name '*.json' | wc -l)" -ge 1500 ]; then
    echo "(v4 already restored: $(find data/triples -name '*.json' | wc -l) triples)"
  else
    tar -xzf data/v4_backup_*.tar.gz
    echo "v4 restored: triples=$(find data/triples -name '*.json' | wc -l)"
    echo "v4 restored: triples_xfamily=$(find data/triples_xfamily -name '*.json' | wc -l)"
  fi
else echo "(no v4 tarball)"; fi

say "3. Verifiers (Dafny 4.11, Lean 4.29 + Mathlib, Verus, Z3)"
bash scripts/install_verifiers.sh || echo "WARN some verifiers may have failed; see docs/REPRODUCIBILITY.md"
export PATH="$PATH:$HOME/.dotnet/tools:$HOME/.elan/bin"

say "4. Lean + Mathlib template (one-time, ~20-40 min)"
TPL="$HOME/lean-project-template"
export TROJANSPEC_LEAN_TEMPLATE="$TPL"
if [ ! -f "$TPL/.mathlib_ready" ]; then
  ( cd "$HOME" && rm -rf lean-project-template && lake new lean-project-template math ) \
   && ( cd "$TPL" && lake exe cache get ) \
   && ( cd "$TPL" && lake build ) && touch "$TPL/.mathlib_ready"
else
  echo "(Mathlib template ready)"
fi

say "5. Phase 7 admission verification (idempotent, skip-already-validated)"
if [ -f data/phase7_admission_report.json ]; then
  echo "(Phase 7 report present: $($PY -c 'import json;print(json.load(open(\"data/phase7_admission_report.json\"))[\"admission_pct\"])')% admission)"
else
  $PY scripts/04_validate_witnesses.py \
    --data-dir data/triples data/triples_xfamily \
    --concurrency 4 --skip-already-validated \
    --timeout 120 --report-json data/phase7_admission_report.json
fi

say "6. Phase 9 SpecGuard evaluation (Bedrock; resumable JSONL)"
if [ -f data/phase9_results_v2.jsonl ]; then
  echo "(Phase 9 v2 jsonl present: $(wc -l < data/phase9_results_v2.jsonl) records)"
  echo "(v2 already includes post-fix axiom_audit verdicts; no re-run needed)"
else
  $PY scripts/06_phase9_eval.py --concurrency 4 \
    --results-jsonl data/phase9_results.jsonl
  $PY scripts/_phase9_axiom_replay.py
  $PY scripts/_phase9_report.py \
    --jsonl data/phase9_results_v2.jsonl \
    --metrics-out data/phase9_metrics_v2.json \
    --report-out docs/phase9_detector_evaluation.md
fi

say "7. Phase 10 post-hoc ablations (zero LLM cost; safe to re-run)"
$PY scripts/10a_elicitor_sweep.py
$PY scripts/10d_ensemble_grid.py
$PY scripts/10e_cross_language.py
$PY scripts/10h_beat_ssc.py 2>/dev/null || echo "(10h needs Phase 10f jsonl + Phase 10g jsonl; skipping)"

say "8. Phase 10i atomic monitor (regenerate JSON + figure if JSONL present)"
if [ -s data/phase10_10i_atomic_results.jsonl ]; then
  $PY scripts/10i_atomic_monitor.py --analyze-only
  echo "(re-aggregated Phase 10i from committed JSONL: F1=$($PY -c 'import json;print(json.load(open(\"data/phase10_10i_atomic.json\"))[\"best_rule_full\"][\"f1\"])'))"
else
  echo "(Phase 10i JSONL not present; trigger full 8192-call run via run_phase10_phase11.sh)"
fi

say "9. Phase 10 LLM-heavy + Phase 11 Mathlib (Bedrock-billed, ~1-2h, ~$11)"
echo "Not auto-run. Trigger explicitly:"
echo "  bash scripts/run_phase10_phase11.sh   # detached; logs /tmp/phase10_11.log"
echo "  tail -f /tmp/phase10_11.log           # markers: PHASE10_11_SUCCESS/DONE"
echo
echo "Stages in that batch: 10b temp, 10c monitor-count, 10f SSC, 10g adaptive,"
echo "                      10h beat-SSC, 10i atomic monitor, 11 Mathlib."

say "DONE - read docs/REPRODUCIBILITY.md for env vars, costs, troubleshooting"
echo "Headline numbers: README.md, STATUS.md, HANDOFF.md."
echo "Phase 10i atomic monitor (the win): docs/phase10i_atomic_monitor.md."
