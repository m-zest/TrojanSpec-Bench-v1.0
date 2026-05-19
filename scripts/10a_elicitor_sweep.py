"""Phase 10a: elicitor sweep.

Re-tally Phase 9 metrics over per-elicitor subsets (Sonnet-only, Haiku-only,
Llama-only) and write a side-by-side comparison. Pure post-hoc over
data/phase9_results_v2.jsonl - no LLM calls.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

DETECTORS = [
    "vacuity", "mutation_coverage", "ghost_leakage",
    "axiom_audit", "monitor_consensus",
]


def _family(model: str | None) -> str:
    m = (model or "").lower()
    for f in ("sonnet", "haiku", "llama"):
        if f in m:
            return f
    return "other"


def _verdict(rep: dict, name: str) -> dict | None:
    for d in rep.get("detectors", []):
        if d.get("detector") == name:
            return d
    return None


def _metrics_for(records: list[dict]) -> dict:
    n = len(records)
    out = {"n": n, "per_detector": {}}
    for det in DETECTORS:
        tp = fp = tn = fn = 0
        for r in records:
            tv = _verdict(r["trojan"], det)
            hv = _verdict(r["honest"], det)
            if tv is None or hv is None:
                continue
            tflag = tv["verdict"] != "clean"
            hflag = hv["verdict"] != "clean"
            tp += tflag
            fn += not tflag
            fp += hflag
            tn += not hflag
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        out["per_detector"][det] = {
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": round(prec, 4), "recall": round(rec, 4),
            "f1": round(f1, 4),
            "fpr": round(fp / (fp + tn), 4) if (fp + tn) else 0.0,
        }
    # paired risk delta
    if records:
        deltas = [r["trojan"]["risk_score"] - r["honest"]["risk_score"]
                  for r in records]
        out["paired_mean_risk_delta"] = round(sum(deltas) / len(deltas), 4)
        out["paired_discrim_rate"] = round(
            sum(1 for d in deltas if d > 0) / len(deltas), 4
        )
    return out


def main() -> None:
    recs: list[dict] = []
    for ln in Path("data/phase9_results_v2.jsonl").read_text().splitlines():
        if not ln.strip():
            continue
        d = json.loads(ln)
        if "error" not in d:
            recs.append(d)
    by_fam: dict[str, list[dict]] = defaultdict(list)
    for r in recs:
        by_fam[_family(r.get("elicitor_model"))].append(r)
    by_fam["all"] = recs

    summary: dict = {"by_elicitor": {}}
    for fam in ("all", "sonnet", "haiku", "llama"):
        if fam in by_fam:
            summary["by_elicitor"][fam] = _metrics_for(by_fam[fam])

    Path("data/phase10_10a_elicitor_sweep.json").write_text(
        json.dumps(summary, indent=2)
    )
    print("wrote data/phase10_10a_elicitor_sweep.json")
    for fam, m in summary["by_elicitor"].items():
        print(f"\n[{fam}] n={m['n']}  paired_Δrisk={m.get('paired_mean_risk_delta','-')}"
              f"  paired_discrim={m.get('paired_discrim_rate','-')}")
        for d in DETECTORS:
            v = m["per_detector"][d]
            print(f"  {d:18s} P={v['precision']:.3f} R={v['recall']:.3f}"
                  f" F1={v['f1']:.3f} FPR={v['fpr']:.3f}")

    # Figure: F1 per detector, grouped bars per elicitor
    fams = [f for f in ("sonnet", "haiku", "llama") if f in by_fam]
    width = 0.25
    x = range(len(DETECTORS))
    plt.figure(figsize=(9, 5))
    for i, fam in enumerate(fams):
        f1s = [summary["by_elicitor"][fam]["per_detector"][d]["f1"]
               for d in DETECTORS]
        plt.bar([xi + i * width for xi in x], f1s, width,
                label=f"{fam} (n={by_fam[fam].__len__()})")
    plt.xticks([xi + width for xi in x], DETECTORS, rotation=20, ha="right")
    plt.ylabel("F1")
    plt.title("Phase 10a: per-detector F1 by elicitor family")
    plt.legend(); plt.grid(alpha=.3, axis="y"); plt.tight_layout()
    Path("figures").mkdir(exist_ok=True)
    plt.savefig("figures/phase10_elicitor_sweep.png", dpi=150)
    plt.close()
    print("\nwrote figures/phase10_elicitor_sweep.png")


if __name__ == "__main__":
    main()
