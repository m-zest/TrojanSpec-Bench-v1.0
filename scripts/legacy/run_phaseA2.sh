#!/usr/bin/env bash
# Phase A2: re-run v2 sanity after compose() fixes; gate >=40%; if pass,
# full regen 5a+5b -> Phase 7 -> final report. Detached; logs /tmp/phaseA2.log.
set -uo pipefail
cd /home/ubuntu/TrojanSpec-Bench-v1.0
export PATH="$PATH:$HOME/.dotnet/tools:$HOME/.elan/bin:$HOME/verus/source/target-verus/release"
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

step "D Lean template check"
[ -f "$TROJANSPEC_LEAN_TEMPLATE/.mathlib_ready" ] && echo "lean template ready" \
  || echo "WARN lean template not marked ready"

step "D sanity regenerate (v2, post-fix, 10 triples)"
rm -rf data/triples_sanity && mkdir -p data/triples_sanity
$PY scripts/02_generate_triples.py --sanity --out-dir data/triples_sanity --concurrency 4
step "D sanity validate"
$PY scripts/04_validate_witnesses.py --data-dir data/triples_sanity --timeout 120 \
   --report-json data/sanity_v2b_report.json
SP=$($PY -c "import json;print(json.load(open('data/sanity_v2b_report.json'))['admission_pct'])")
echo "SANITY_V2B_ADMISSION=$SP%"
gitci "phase5-redux: post-fix v2 sanity report ($SP% admission)"
if ! awk "BEGIN{exit !($SP>=40)}"; then
  echo "PHASEA2_STOPPED_SANITY: $SP% < 40% gate - NOT regenerating"
  echo "PHASEA2_DONE $(date -u +%H:%M:%S)"; exit 1
fi

step "E 5a full generation (1500, qwen2.5:32b)"
$PY scripts/02_generate_triples.py --concurrency 4 > /tmp/main_v2.log 2>&1
$PY scripts/_phase5_summary.py data/triples phase5a 1500 >> /tmp/main_v2.log 2>&1
step "E 5b ablation (300)"
$PY scripts/02_generate_triples.py --xfamily --concurrency 4 > /tmp/xfamily_v2.log 2>&1
$PY scripts/_phase5_summary.py data/triples_xfamily phase5b 300 >> /tmp/xfamily_v2.log 2>&1

step "F Phase 7 validation (v2)"
$PY scripts/04_validate_witnesses.py --data-dir data/triples data/triples_xfamily \
   --timeout 120 --report-json data/phase7_admission_report.json
DL=$($PY -c "import json;d=json.load(open('data/phase7_admission_report.json'))['by_language'];a=sum(d.get(k,{}).get('admitted',0) for k in('dafny','lean'));t=sum(d.get(k,{}).get('total',0) for k in('dafny','lean'));print(round(100*a/t,1) if t else 0)")
echo "PHASE7_DAFNY_LEAN_ADMISSION=$DL%"
gitci "phase7: v2 admission report (Dafny + Lean only; Verus deferred)"
if ! awk "BEGIN{exit !($DL>=50)}"; then
  echo "PHASEA2_STOPPED_PHASE7: Dafny+Lean $DL% < 50%"
  echo "PHASEA2_DONE $(date -u +%H:%M:%S)"; exit 1
fi

step "G final report"
$PY scripts/_phase_final_report.py
gitci "phase8: final v1-vs-v2 completion report; pipeline through Phase 7 complete"
echo "PHASEA2_SUCCESS Dafny+Lean=$DL%"
echo "PHASEA2_DONE $(date -u +%H:%M:%S)"
