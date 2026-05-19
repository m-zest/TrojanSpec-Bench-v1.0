#!/usr/bin/env bash
# Phase A4 parallel resume: 5a+5b already generated and Phase 7 was ~513/1798
# validated when interrupted. Resume Phase 7 with 4-way ProcessPool +
# --skip-already-validated (already-validated triples preserved & still
# counted), then gate Dafny+Lean >=50% -> final v1->v4 progression report.
# Detached; logs /tmp/phaseA4_parallel.log.
set -uo pipefail
cd /home/ubuntu/TrojanSpec-Bench-v1.0
export PATH="$PATH:$HOME/.dotnet/tools:$HOME/.elan/bin"
export TROJANSPEC_LEAN_TEMPLATE="$HOME/lean-project-template"
PY=./venv/bin/python
BR=claude/professional-search-interface-MCp22
gitci(){ git -c user.name="Mohammad Zeeshan" -c user.email="hdglit@inf.elte.hu" \
  add -A ":!data/triples_v1" ":!data/triples_xfamily_v1" ":!data/*.tar.gz" \
  ":!data/triples_v1_old_*" ":!data/triples_xfamily_v1_old_*" 2>/dev/null; \
  git -c user.name="Mohammad Zeeshan" -c user.email="hdglit@inf.elte.hu" \
  commit --author="Mohammad Zeeshan <hdglit@inf.elte.hu>" -q -m "$1" 2>/dev/null \
  && git push origin "$BR" 2>&1 | tail -1 || echo "(nothing to commit: $1)"; }
step(){ echo "=== $1 $(date -u +%H:%M:%S) ==="; }

step "F Phase 7 parallel resume (concurrency=4, skip already validated)"
$PY scripts/04_validate_witnesses.py \
   --data-dir data/triples data/triples_xfamily \
   --concurrency 4 --skip-already-validated \
   --timeout 120 --report-json data/phase7_admission_report.json
RC=$?
if [ $RC -ne 0 ]; then
  echo "PHASEA4_STOPPED_PHASE7: validator exited $RC (no success commit)"
  echo "PHASEA4_DONE $(date -u +%H:%M:%S)"; exit 1
fi
DL=$($PY -c "import json;d=json.load(open('data/phase7_admission_report.json'))['by_language'];a=sum(d.get(k,{}).get('admitted',0) for k in('dafny','lean'));t=sum(d.get(k,{}).get('total',0) for k in('dafny','lean'));print(round(100*a/t,1) if t else 0)")
echo "PHASE7_DAFNY_LEAN_ADMISSION=$DL%"
gitci "phase7: v4 admission report (parallel resume; Dafny + Lean; Verus deferred)"
if ! awk "BEGIN{exit !($DL>=50)}"; then
  echo "PHASEA4_STOPPED_PHASE7: Dafny+Lean $DL% < 50% (no success commit)"
  echo "PHASEA4_DONE $(date -u +%H:%M:%S)"; exit 1
fi

step "G final v1->v4 progression report"
$PY scripts/_phase_final_report.py
gitci "phase5-to-8: final v1->v4 progression report; pipeline through Phase 7 complete"
echo "PHASEA4_SUCCESS Dafny+Lean=$DL%"
echo "PHASEA4_DONE $(date -u +%H:%M:%S)"
