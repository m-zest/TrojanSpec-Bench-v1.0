"""Phase 10d: detector ensemble grid search.

For each non-empty subset of the 5 detectors (31 subsets), compute the
combined-risk verdict using the same weighting as ``combined_risk`` and
report P/R/F1 on the trojan/honest set. The "best subset by F1" gives the
minimum-cost ensemble that still hits the headline number. Pure post-hoc
over data/phase9_results_v2.jsonl - no LLM calls.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from trojanspec.specguard.base import DetectorResult, Verdict, combined_risk

DETECTORS = [
    "vacuity", "mutation_coverage", "ghost_leakage",
    "axiom_audit", "monitor_consensus",
]
# LLM cost per triple for the ensemble pricing column.
COST = dict.fromkeys(DETECTORS, 0) | {"monitor_consensus": 3}


def _detector_results(report: dict, names: tuple[str, ...]) -> list[DetectorResult]:
    """Reconstruct DetectorResult objects for the chosen subset."""
    out = []
    for d in report.get("detectors", []):
        if d["detector"] in names:
            out.append(DetectorResult(
                detector=d["detector"],
                verdict=Verdict(d["verdict"]),
                evidence=d.get("evidence", []),
                detail=d.get("detail", {}),
            ))
    return out


def _metrics(recs: list[dict], subset: tuple[str, ...]) -> dict:
    tp = fp = tn = fn = 0
    for r in recs:
        t_drs = _detector_results(r["trojan"], subset)
        h_drs = _detector_results(r["honest"], subset)
        if not t_drs or not h_drs:
            continue
        tflag = combined_risk(t_drs)[0] is not Verdict.CLEAN
        hflag = combined_risk(h_drs)[0] is not Verdict.CLEAN
        tp += tflag
        fn += not tflag
        fp += hflag
        tn += not hflag
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": round(prec, 4), "recall": round(rec, 4),
        "f1": round(f1, 4),
        "fpr": round(fp / (fp + tn), 4) if (fp + tn) else 0.0,
        "cost": sum(COST[d] for d in subset),
    }


def main() -> None:
    recs: list[dict] = []
    for ln in Path("data/phase9_results_v2.jsonl").read_text().splitlines():
        if ln.strip():
            d = json.loads(ln)
            if "error" not in d:
                recs.append(d)
    print(f"loaded {len(recs)} records")

    subsets: list[tuple[str, ...]] = []
    for k in range(1, len(DETECTORS) + 1):
        subsets.extend(itertools.combinations(DETECTORS, k))

    grid = []
    for s in subsets:
        m = _metrics(recs, s)
        grid.append({"subset": list(s), "size": len(s), **m})

    grid.sort(key=lambda x: (-x["f1"], x["cost"], x["size"]))
    best = grid[0]
    cheapest_max = min(
        (g for g in grid if g["f1"] >= best["f1"] - 1e-9),
        key=lambda x: (x["cost"], x["size"]),
    )

    summary = {
        "n_records": len(recs),
        "best_by_f1": best,
        "cheapest_at_best_f1": cheapest_max,
        "grid": grid,
    }
    Path("data/phase10_10d_ensemble_grid.json").write_text(
        json.dumps(summary, indent=2)
    )
    print("wrote data/phase10_10d_ensemble_grid.json")
    print(f"\nbest by F1: subset={best['subset']} F1={best['f1']:.3f} "
          f"P={best['precision']:.3f} R={best['recall']:.3f} cost={best['cost']}")
    print(f"cheapest at max F1: subset={cheapest_max['subset']} "
          f"F1={cheapest_max['f1']:.3f} cost={cheapest_max['cost']}")
    print("\ntop-10 subsets by F1:")
    for g in grid[:10]:
        print(f"  F1={g['f1']:.3f}  P={g['precision']:.3f}  R={g['recall']:.3f}"
              f"  FPR={g['fpr']:.3f}  cost={g['cost']}  {g['subset']}")

    # Pareto: cost vs F1 (one point per subset, best-F1 envelope highlighted)
    plt.figure(figsize=(7, 5))
    plt.scatter([g["cost"] for g in grid], [g["f1"] for g in grid],
                s=20, alpha=.5, label="all 31 subsets")
    # Pareto frontier: for each unique cost, best F1
    by_cost: dict[int, float] = {}
    by_cost_sub: dict[int, list[str]] = {}
    for g in grid:
        if g["f1"] > by_cost.get(g["cost"], -1):
            by_cost[g["cost"]] = g["f1"]
            by_cost_sub[g["cost"]] = g["subset"]
    pareto_x = sorted(by_cost)
    pareto_y = [by_cost[c] for c in pareto_x]
    plt.plot(pareto_x, pareto_y, "-o", color="red",
             label="Pareto frontier", linewidth=2)
    for c in pareto_x:
        plt.annotate(",".join(d[:3] for d in by_cost_sub[c]),
                     (c, by_cost[c]), textcoords="offset points",
                     xytext=(6, 4), fontsize=7)
    plt.xlabel("Cost per triple (LLM monitor calls)")
    plt.ylabel("F1 (combined-risk verdict)")
    plt.title("Phase 10d: detector subset ensemble Pareto")
    plt.grid(alpha=.3)
    plt.legend()
    plt.tight_layout()
    Path("figures").mkdir(exist_ok=True)
    plt.savefig("figures/phase10_ensemble_grid.png", dpi=150)
    plt.close()
    print("\nwrote figures/phase10_ensemble_grid.png")


if __name__ == "__main__":
    main()
