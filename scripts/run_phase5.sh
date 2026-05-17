#!/usr/bin/env bash
# Phase 5a (top up data/triples/ to 1500 with local Ollama Qwen-2.5-32B;
# keeps the 90 existing Fireworks gpt-oss triples) then Phase 5b (300
# cross-family ablation triples, Qwen-Coder + DeepSeek-Coder 50/50).
#
# Local Ollama backend; no API key needed. Does NOT delete existing triples
# (the generation script resumes by topping each cell up to quota).
set -uo pipefail
cd "$(dirname "$0")/.."

PY=./venv/bin/python
[ -x "$PY" ] || PY=python

echo "=== PHASE 5a START $(date -u +%H:%M:%S) ===" >> /tmp/main_ollama.log
$PY scripts/02_generate_triples.py --concurrency 4 >> /tmp/main_ollama.log 2>&1
echo "5a_exit=$?" >> /tmp/main_ollama.log
$PY scripts/_phase5_summary.py data/triples phase5a 1500 >> /tmp/main_ollama.log 2>&1

echo "=== PHASE 5b START $(date -u +%H:%M:%S) ===" >> /tmp/xfamily_ollama.log
$PY scripts/02_generate_triples.py --xfamily --concurrency 4 \
    >> /tmp/xfamily_ollama.log 2>&1
echo "5b_exit=$?" >> /tmp/xfamily_ollama.log
$PY scripts/_phase5_summary.py data/triples_xfamily phase5b 300 \
    >> /tmp/xfamily_ollama.log 2>&1

echo "CHAIN_DONE $(date -u +%H:%M:%S)" >> /tmp/xfamily_ollama.log
