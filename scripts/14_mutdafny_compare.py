"""Phase 14 step 6: head-to-head on the 319 admitted Dafny triples.

Three detectors:
  A. our ``mutation_coverage`` (paired, from ``data/phase9_results_v2.jsonl``)
  B. MutDafny (Amaral et al. arXiv:2511.15403; from
     ``data/phase14_mutdafny_{honest,trojan}_results.jsonl``)
  C. ``atomic_monitor`` K=2 of 4 (Phase 10i; from
     ``data/phase10_10i_atomic_results.jsonl``)

Emits the 2×2 contingency atomic-vs-MutDafny and ours-vs-MutDafny on the trojan
side, with McNemar exact two-sided p-values. Pure-Python, no external deps.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path


def _load_jsonl(p: Path) -> list[dict]:
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def _f1pr(tp: int, fp: int, tn: int, fn: int) -> dict:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": round(p, 4), "recall": round(r, 4),
            "f1": round(f, 4), "fpr": round(fpr, 4)}


def _mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar test under Binomial(n, 0.5)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    s = sum(math.comb(n, i) for i in range(k + 1))
    return min(1.0, 2 * (s / (2 ** n)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--phase9",      default="data/phase9_results_v2.jsonl")
    ap.add_argument("--atomic",      default="data/phase10_10i_atomic_results.jsonl")
    ap.add_argument("--mut-honest",  default="data/phase14_mutdafny_honest_results.jsonl")
    ap.add_argument("--mut-trojan",  default="data/phase14_mutdafny_trojan_results.jsonl")
    ap.add_argument("--out",         default="data/phase14_h2h_summary.json")
    args = ap.parse_args()

    ours_by_tid: dict[str, dict] = {}
    for line in Path(args.phase9).read_text().splitlines():
        r = json.loads(line)
        if r.get("language") != "dafny":
            continue
        tid = r["triple_id"]
        def mc(side: dict) -> bool:
            for d in side.get("detectors", []):
                if d.get("detector") == "mutation_coverage":
                    return d.get("verdict") in ("malicious", "suspicious")
            return False
        ours_by_tid[tid] = {
            "ours_trojan_flag": mc(r["trojan"]),
            "ours_honest_flag": mc(r["honest"]),
            "attack_pattern": r.get("attack_pattern"),
        }

    atomic_by_tid: dict[str, dict] = {}
    for line in Path(args.atomic).read_text().splitlines():
        r = json.loads(line)
        if r.get("language") != "dafny":
            continue
        atomic_by_tid[r["triple_id"]] = {
            "atomic_trojan_flag": r["trojan"]["failures"] >= 2,
            "atomic_honest_flag": r["honest"]["failures"] >= 2,
            "trojan_failures":    r["trojan"]["failures"],
            "honest_failures":    r["honest"]["failures"],
        }

    md_honest = {r["triple_id"]: r for r in _load_jsonl(Path(args.mut_honest))}
    md_trojan = {r["triple_id"]: r for r in _load_jsonl(Path(args.mut_trojan))}

    common = sorted(set(ours_by_tid) & set(atomic_by_tid) & set(md_honest) & set(md_trojan))
    n = len(common)

    def metrics(trojan_set: set, honest_set: set) -> dict:
        tp = sum(1 for t in common if t in trojan_set)
        fn = n - tp
        fp = sum(1 for t in common if t in honest_set)
        tn = n - fp
        return _f1pr(tp, fp, tn, fn)

    ours_pos       = {t for t in common if ours_by_tid[t]["ours_trojan_flag"]}
    ours_honest    = {t for t in common if ours_by_tid[t]["ours_honest_flag"]}
    md_pos         = {t for t in common if md_trojan[t]["mutdafny_flag"]}
    md_honest_pos  = {t for t in common if md_honest[t]["mutdafny_flag"]}
    atom_pos       = {t for t in common if atomic_by_tid[t]["atomic_trojan_flag"]}
    atom_honest    = {t for t in common if atomic_by_tid[t]["atomic_honest_flag"]}

    M_ours = metrics(ours_pos, ours_honest)
    M_md   = metrics(md_pos,   md_honest_pos)
    M_atom = metrics(atom_pos, atom_honest)

    attacks = sorted({ours_by_tid[t]["attack_pattern"] for t in common})
    per_attack = {}
    for ap_ in attacks:
        tids = [t for t in common if ours_by_tid[t]["attack_pattern"] == ap_]
        n_ap = len(tids)
        per_attack[ap_] = {
            "n_trojans":         n_ap,
            "ours_recall":       round(sum(1 for t in tids if t in ours_pos) / n_ap, 4),
            "ours_flagged":      sum(1 for t in tids if t in ours_pos),
            "mutdafny_recall":   round(sum(1 for t in tids if t in md_pos)   / n_ap, 4),
            "mutdafny_flagged":  sum(1 for t in tids if t in md_pos),
            "atomic_recall":     round(sum(1 for t in tids if t in atom_pos) / n_ap, 4),
            "atomic_flagged":    sum(1 for t in tids if t in atom_pos),
        }

    # atomic vs MutDafny (trojan side)
    both_am   = atom_pos & md_pos
    atom_only = atom_pos - md_pos
    md_only_a = md_pos - atom_pos
    neither_am = (set(common) - atom_pos) - md_pos
    p_atom_md = _mcnemar_exact(len(atom_only), len(md_only_a))

    # ours vs MutDafny (trojan side)
    both_om    = ours_pos & md_pos
    ours_only  = ours_pos - md_pos
    md_only_o  = md_pos - ours_pos
    neither_om = (set(common) - ours_pos) - md_pos
    p_ours_md  = _mcnemar_exact(len(ours_only), len(md_only_o))

    md_walls = [md_trojan[t]["wall_sec"] for t in common] + \
               [md_honest[t]["wall_sec"] for t in common]
    md_time = {
        "median_sec": round(statistics.median(md_walls), 2),
        "p95_sec":    round(sorted(md_walls)[int(0.95 * len(md_walls)) - 1], 2),
        "total_cpu_sec": round(sum(md_walls), 1),
        "total_cpu_min": round(sum(md_walls) / 60, 1),
    }

    summary = {
        "n_common_dafny": n,
        "ours_metrics_dafny":    M_ours,
        "mutdafny_metrics_dafny":M_md,
        "atomic_metrics_dafny":  M_atom,
        "delta_f1_atomic_minus_mutdafny": round(M_atom["f1"] - M_md["f1"], 4),
        "delta_f1_ours_minus_mutdafny":   round(M_ours["f1"] - M_md["f1"], 4),
        "per_attack_recall": per_attack,
        "contingency_atomic_vs_mutdafny_trojan_side": {
            "atomic_AND_mutdafny": len(both_am),
            "atomic_only":         len(atom_only),
            "mutdafny_only":       len(md_only_a),
            "neither":             len(neither_am),
        },
        "mcnemar_p_atomic_vs_mutdafny_trojan": round(p_atom_md, 6),
        "contingency_ours_vs_mutdafny_trojan_side": {
            "ours_AND_mutdafny": len(both_om),
            "ours_only":         len(ours_only),
            "mutdafny_only":     len(md_only_o),
            "neither":           len(neither_om),
        },
        "mcnemar_p_ours_vs_mutdafny_trojan": round(p_ours_md, 6),
        "mutdafny_compute_time_dafny_subset": md_time,
        "edge_cases": {
            "mutdafny_zero_mutant_honest": [
                t for t in common if md_honest[t]["n_mutants_generated"] == 0
            ],
            "mutdafny_zero_mutant_trojan": [
                t for t in common if md_trojan[t]["n_mutants_generated"] == 0
            ],
        },
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
