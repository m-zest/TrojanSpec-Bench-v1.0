#!/usr/bin/env bash
# Phase 5a (1500 triples, gpt-oss only) then Phase 5b (300 triples,
# deepseek+kimi 50/50). Run from the repo root with the venv active or with
# ./venv present. Logs stream to /tmp/main1500.log and /tmp/xfamily300.log.
#
# NOTE: requires a Fireworks key with adequate requests-per-minute. The low
# default-tier key 429s a 1500-job burst (see STATUS.md section 3).
set -uo pipefail
cd "$(dirname "$0")/.."

PY=./venv/bin/python
[ -x "$PY" ] || PY=python

# Clear sanity leftovers and any prior ablation data.
rm -rf data/triples/dafny data/triples/lean data/triples/verus data/triples_xfamily

echo "=== PHASE 5a START $(date -u +%H:%M:%S) ===" >> /tmp/main1500.log
$PY scripts/02_generate_triples.py --concurrency 8 >> /tmp/main1500.log 2>&1
echo "5a_exit=$?" >> /tmp/main1500.log
$PY scripts/_phase5_summary.py data/triples phase5a 1500 >> /tmp/main1500.log 2>&1

echo "=== PHASE 5b START $(date -u +%H:%M:%S) ===" >> /tmp/xfamily300.log
$PY scripts/02_generate_triples.py --families fireworks-deepseek fireworks-kimi \
    --out-dir data/triples_xfamily --per-cell 25 --concurrency 8 \
    >> /tmp/xfamily300.log 2>&1
echo "5b_exit=$?" >> /tmp/xfamily300.log
$PY scripts/_phase5_summary.py data/triples_xfamily phase5b 300 >> /tmp/xfamily300.log 2>&1

echo "CHAIN_DONE $(date -u +%H:%M:%S)" >> /tmp/xfamily300.log
