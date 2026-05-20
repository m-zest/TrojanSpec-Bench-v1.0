#!/usr/bin/env bash
# Phase 14 orchestrator — head-to-head MutDafny (Amaral et al., arXiv:2511.15403)
# vs our static mutation_coverage + Phase-10i atomic_monitor on the Dafny subset.
#
# Prereq: bash scripts/install_mutdafny.sh   (one-time, ~20 min)
# Wall clock for this script: ~50 min (Steps 4 + 5 at concurrency 4; Step 6
# is pure-Python aggregation, seconds).
set -uo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-./venv/bin/python}
MUTDAFNY_HOME=${MUTDAFNY_HOME:-$HOME/tools/mutdafny}
INPUTS=/tmp/mutdafny_inputs
HONEST_JSONL=data/phase14_mutdafny_honest_results.jsonl
HONEST_JSON=data/phase14_mutdafny_honest_summary.json
TROJAN_JSONL=data/phase14_mutdafny_trojan_results.jsonl
TROJAN_JSON=data/phase14_mutdafny_trojan_summary.json
H2H_JSON=data/phase14_h2h_summary.json

say(){ echo; echo "######## $* ########"; }

if [ ! -x "$MUTDAFNY_HOME/run.sh" ]; then
  echo "ERROR: MutDafny not installed at $MUTDAFNY_HOME"
  echo "Run: bash scripts/install_mutdafny.sh"
  exit 2
fi

say "Step 3 — extract 319 Dafny pairs into $INPUTS"
$PY scripts/14_mutdafny_extract_pairs.py --out-dir "$INPUTS"

say "Step 4 — MutDafny on 319 HONEST specs (resumable; ~33 min @ concurrency 4)"
$PY scripts/14_mutdafny_batch.py \
    --side honest \
    --inputs-dir "$INPUTS" \
    --out-jsonl "$HONEST_JSONL" \
    --summary-json "$HONEST_JSON" \
    --mutdafny-home "$MUTDAFNY_HOME" \
    --concurrency 4

say "Step 5 — MutDafny on 319 TROJAN specs (resumable; ~16 min @ concurrency 4)"
$PY scripts/14_mutdafny_batch.py \
    --side trojan \
    --inputs-dir "$INPUTS" \
    --out-jsonl "$TROJAN_JSONL" \
    --summary-json "$TROJAN_JSON" \
    --mutdafny-home "$MUTDAFNY_HOME" \
    --concurrency 4

say "Step 6 — head-to-head: ours vs MutDafny vs atomic_monitor (Dafny only)"
$PY scripts/14_mutdafny_compare.py \
    --out "$H2H_JSON"

say "PHASE14_SUCCESS — see $H2H_JSON and MUTDAFNY_COMPARISON.md"
