#!/usr/bin/env bash
# Phase 9: SpecGuard detector evaluation against the 1024 admitted triples
# + 1024 honest controls. Streams to data/phase9_results.jsonl (resumable),
# then aggregates -> metrics.json + 3 figures + markdown report.
# Detached; logs /tmp/phase9_eval.log.
set -uo pipefail
cd /home/ubuntu/TrojanSpec-Bench-v1.0
export PATH="$PATH:$HOME/.dotnet/tools:$HOME/.elan/bin"
PY=./venv/bin/python
BR=claude/professional-search-interface-MCp22
gitci(){ git -c user.name="Mohammad Zeeshan" -c user.email="hdglit@inf.elte.hu" \
  add -A ":!data/triples_v1" ":!data/triples_xfamily_v1" ":!data/*.tar.gz"; \
  git -c user.name="Mohammad Zeeshan" -c user.email="hdglit@inf.elte.hu" \
  commit --author="Mohammad Zeeshan <hdglit@inf.elte.hu>" -q -m "$1" 2>/dev/null \
  && git push origin "$BR" 2>&1 | tail -1 || echo "(nothing to commit: $1)"; }
step(){ echo "=== $1 $(date -u +%H:%M:%S) ==="; }

step "H phase9 eval (5 detectors x 1024 trojan + 1024 honest, c=4)"
$PY scripts/06_phase9_eval.py --concurrency 4 \
   --results-jsonl data/phase9_results.jsonl
RC=$?
if [ $RC -ne 0 ]; then
  echo "PHASE9_STOPPED: eval exit $RC (check log for STOP guard)"
  echo "PHASE9_DONE $(date -u +%H:%M:%S)"; exit 1
fi

step "I phase9 report + figures"
$PY scripts/_phase9_report.py
gitci "phase9: detector evaluation on 1024 admitted triples"
echo "PHASE9_SUCCESS"
echo "PHASE9_DONE $(date -u +%H:%M:%S)"
