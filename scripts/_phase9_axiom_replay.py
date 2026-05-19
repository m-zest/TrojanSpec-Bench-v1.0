"""Replay the (post-fix) axiom_audit detector over the existing Phase 9
results jsonl, splicing the new verdict in place of the old one.

No LLM calls. Writes a new jsonl alongside the original so the delta is
auditable, plus a small delta-summary on stdout.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from trojanspec.specguard import AxiomAuditDetector, combined_risk
from trojanspec.specguard.base import DetectorResult, Verdict


def _load_triple_index() -> dict[str, dict]:
    """triple_id -> source triple JSON (across both data dirs)."""
    idx: dict[str, dict] = {}
    for root in ("data/triples", "data/triples_xfamily"):
        for f in Path(root).rglob("*.json"):
            if f.name.endswith("_SUMMARY.json"):
                continue
            try:
                t = json.loads(f.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            tid = t.get("triple_id")
            if tid:
                idx[tid] = t
    return idx


def _rerun_axiom(triple: dict, det: AxiomAuditDetector,
                 honest_side: bool) -> dict:
    """Run axiom_audit; honest_side=True replaces trojan_spec with original."""
    view = dict(triple)
    if honest_side:
        view["trojan_spec"] = triple.get("original_spec", "")
        # The leak surface in `preamble` is shared in v3 composition - but for
        # the honest control we want to know whether the spec under inspection
        # introduces unverified surface. Reuse the same preamble; the diff
        # against original_spec naturally suppresses honest-only constructs.
    return det.scan(view).as_dict()


def _splice(report: dict, new_axiom: dict) -> dict:
    """Replace the axiom_audit detector entry; recompute combined risk."""
    detectors = [d for d in report.get("detectors", [])
                 if d.get("detector") != "axiom_audit"]
    detectors.append(new_axiom)
    # combined_risk takes DetectorResult; reconstruct lightly.
    drs = [
        DetectorResult(
            detector=d["detector"],
            verdict=Verdict(d["verdict"]),
            evidence=d.get("evidence", []),
            detail=d.get("detail", {}),
        ) for d in detectors
    ]
    verdict, risk = combined_risk(drs)
    return {
        **report,
        "overall_verdict": verdict.value,
        "risk_score": risk,
        "detectors": detectors,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-jsonl", default="data/phase9_results.jsonl")
    ap.add_argument("--out-jsonl", default="data/phase9_results_v2.jsonl")
    args = ap.parse_args()

    idx = _load_triple_index()
    print(f"loaded source triples: {len(idx)}")
    det = AxiomAuditDetector()

    n = 0
    old_troj_flag = old_hon_flag = new_troj_flag = new_hon_flag = 0
    with open(args.in_jsonl) as fin, open(args.out_jsonl, "w") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if "error" in rec or rec.get("triple_id") not in idx:
                fout.write(line + "\n")
                continue
            tid = rec["triple_id"]
            t = idx[tid]
            old_t = next((d for d in rec["trojan"]["detectors"]
                          if d["detector"] == "axiom_audit"), None)
            old_h = next((d for d in rec["honest"]["detectors"]
                          if d["detector"] == "axiom_audit"), None)
            new_t = _rerun_axiom(t, det, honest_side=False)
            new_h = _rerun_axiom(t, det, honest_side=True)
            rec["trojan"] = _splice(rec["trojan"], new_t)
            rec["honest"] = _splice(rec["honest"], new_h)
            n += 1
            if old_t and old_t["verdict"] != "clean":
                old_troj_flag += 1
            if old_h and old_h["verdict"] != "clean":
                old_hon_flag += 1
            if new_t["verdict"] != "clean":
                new_troj_flag += 1
            if new_h["verdict"] != "clean":
                new_hon_flag += 1
            fout.write(json.dumps(rec) + "\n")

    print(f"replayed {n} records -> {args.out_jsonl}")
    print()
    print("axiom_audit DELTA (trojan flagged | honest flagged):")
    print(f"  old detector: trojan {old_troj_flag:4d}/{n}  honest {old_hon_flag:4d}/{n}")
    print(f"  new detector: trojan {new_troj_flag:4d}/{n}  honest {new_hon_flag:4d}/{n}")
    print(f"  +trojan TP : {new_troj_flag - old_troj_flag:+d}")
    print(f"  +honest FP : {new_hon_flag - old_hon_flag:+d}")


if __name__ == "__main__":
    main()
