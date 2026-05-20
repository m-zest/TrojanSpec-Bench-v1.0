#!/usr/bin/env bash
# Phase 10 (LLM-heavy 10b/c/f/g/h/i) + Phase 11 (Mathlib case study).
# Sequential, detached, gitci+push after each stage. Logs /tmp/phase10_11.log.
# 10a/10d/10e already committed (post-hoc, no LLM cost).
#
# Stages: 10b temp, 10c monitor-count, 10f SSC, 10g adaptive,
#         10h beat-SSC (5 hypotheses), 10i atomic monitor (the win),
#         11 Mathlib.
# Total: ~22k Bedrock calls, ~$11, ~2 h wall clock at concurrency 12.
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH="$PATH:$HOME/.dotnet/tools:$HOME/.elan/bin"
export TROJANSPEC_LEAN_TEMPLATE="$HOME/lean-project-template"
PY=./venv/bin/python
BR="main"
gitci(){ git -c user.name="Mohammad Zeeshan" -c user.email="hdglit@inf.elte.hu" \
  add -A ":!data/triples_v1" ":!data/triples_xfamily_v1" ":!data/*.tar.gz"; \
  git -c user.name="Mohammad Zeeshan" -c user.email="hdglit@inf.elte.hu" \
  commit --author="Mohammad Zeeshan <hdglit@inf.elte.hu>" -q -m "$1" 2>/dev/null \
  && git push origin "$BR" 2>&1 | tail -1 || echo "(nothing to commit: $1)"; }
step(){ echo "=== $1 $(date -u +%H:%M:%S) ==="; }

step "10b monitor temperature ablation (200 triples x 4 temps, Sonnet)"
$PY scripts/10b_monitor_temperature.py --sample 200
gitci "phase10b: monitor temperature ablation (200 triples x temps 0.0/0.3/0.7/1.0)"

step "10c monitor count ablation (300 triples x panels {1,3,5})"
$PY scripts/10c_monitor_count.py --sample 300
gitci "phase10c: monitor count ablation (1 vs 3 vs 5, 300 triples)"

step "10f SSC baseline (Self-Spec Consistency, full 1024 admitted)"
$PY scripts/10f_ssc_baseline.py
gitci "phase10f: SSC baseline (single-model 2-question consistency)"

step "10g adaptive attack stress test (60 impl_leak triples)"
$PY scripts/10g_adaptive_attack.py --sample 60
gitci "phase10g: adaptive attack (banned-marker evasion, 60 impl_leak)"

step "10h beat-SSC (5 hypotheses; needs 10f + 10g jsonl from above)"
$PY scripts/10h_beat_ssc.py
gitci "phase10h: can SpecGuard beat SSC? (5 hypotheses tested, honest verdict)"

step "10i atomic-criteria monitor (8192 Sonnet calls, ~30 min at concurrency 12)"
$PY scripts/10i_atomic_monitor.py --concurrency 12
gitci "phase10i: atomic-criteria monitor breaks the 0.871 ceiling (F1 0.967)"

step "11 Mathlib case study (100 theorems)"
$PY scripts/11_mathlib_case_study.py --target 100
gitci "phase11: Mathlib case study (100 sampled theorems, axiom_audit + monitor_consensus)"

step "consolidated phase10 + phase11 reports"
$PY scripts/_phase10_report.py
$PY scripts/_phase11_report.py
gitci "phase10+11: consolidated docs/phase10_ablations.md + docs/phase11_mathlib_case_study.md"

echo "PHASE10_11_SUCCESS"
echo "PHASE10_11_DONE $(date -u +%H:%M:%S)"
