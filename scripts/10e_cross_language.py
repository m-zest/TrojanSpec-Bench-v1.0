"""Phase 10e: cross-language transfer.

Train a combined-risk threshold on one language (the threshold maximizing
F1 on that language's records) and apply the same threshold to the other
two languages. If a detector ensemble generalises, the F1 across languages
should be close to the in-language F1. Pure post-hoc - no LLM calls.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

LANGS = ["dafny", "lean", "verus"]


def _best_threshold(recs: list[dict]) -> tuple[float, float]:
    """Return (threshold, F1) maximizing F1 on this subset."""
    troj = [r["trojan"]["risk_score"] for r in recs]
    hon = [r["honest"]["risk_score"] for r in recs]
    if not troj or not hon:
        return 0.0, 0.0
    candidates = sorted({round(s, 3) for s in troj + hon} | {0.0, 1.0 + 1e-9})
    best_thr, best_f1 = 0.0, -1.0
    for thr in candidates:
        tp = sum(1 for s in troj if s >= thr)
        fp = sum(1 for s in hon if s >= thr)
        fn = len(troj) - tp
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        if f1 > best_f1:
            best_f1, best_thr = f1, thr
    return best_thr, best_f1


def _eval_at(recs: list[dict], thr: float) -> dict:
    troj = [r["trojan"]["risk_score"] for r in recs]
    hon = [r["honest"]["risk_score"] for r in recs]
    if not troj or not hon:
        return {"n": 0, "precision": 0.0, "recall": 0.0, "f1": 0.0, "fpr": 0.0}
    tp = sum(1 for s in troj if s >= thr)
    fp = sum(1 for s in hon if s >= thr)
    fn = len(troj) - tp
    tn = len(hon) - fp
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {
        "n": len(troj),
        "precision": round(prec, 4), "recall": round(rec, 4),
        "f1": round(f1, 4),
        "fpr": round(fp / (fp + tn), 4) if (fp + tn) else 0.0,
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
    }


def main() -> None:
    recs: list[dict] = []
    for ln in Path("data/phase9_results_v2.jsonl").read_text().splitlines():
        if ln.strip():
            d = json.loads(ln)
            if "error" not in d:
                recs.append(d)
    by_lang: dict[str, list[dict]] = defaultdict(list)
    for r in recs:
        by_lang[r["language"]].append(r)
    print({k: len(v) for k, v in by_lang.items()})

    # train on lang A, apply to A/B/C; matrix[A][B] = F1 when trained on A,
    # evaluated on B.
    matrix: dict[str, dict] = {}
    thresholds: dict[str, float] = {}
    for tr in LANGS:
        thr, in_f1 = _best_threshold(by_lang[tr])
        thresholds[tr] = thr
        matrix[tr] = {"threshold": thr, "in_lang_f1": round(in_f1, 4), "applied_to": {}}
        for ev in LANGS:
            matrix[tr]["applied_to"][ev] = _eval_at(by_lang[ev], thr)

    summary = {
        "n_records": len(recs),
        "per_language_n": {k: len(v) for k, v in by_lang.items()},
        "thresholds_chosen": thresholds,
        "matrix": matrix,
    }
    Path("data/phase10_10e_cross_language.json").write_text(
        json.dumps(summary, indent=2)
    )
    print("wrote data/phase10_10e_cross_language.json\n")

    # Compact text matrix
    header = "train|eval"
    print(f"{header:<12}", *[f"{ev:>8}" for ev in LANGS], "  thr")
    for tr in LANGS:
        cells = [f"{matrix[tr]['applied_to'][ev]['f1']:.3f}" for ev in LANGS]
        print(f"{tr:<12}", *[f"{c:>8}" for c in cells],
              f"  {matrix[tr]['threshold']:.3f}")

    # Figure: 3x3 heatmap of F1
    fig, ax = plt.subplots(figsize=(5.5, 5))
    mat = [[matrix[tr]["applied_to"][ev]["f1"] for ev in LANGS] for tr in LANGS]
    im = ax.imshow(mat, vmin=0, vmax=1, cmap="viridis")
    ax.set_xticks(range(len(LANGS)))
    ax.set_xticklabels([f"eval: {la}" for la in LANGS])
    ax.set_yticks(range(len(LANGS)))
    ax.set_yticklabels([f"train: {la}" for la in LANGS])
    for i in range(len(LANGS)):
        for j in range(len(LANGS)):
            ax.text(j, i, f"{mat[i][j]:.2f}", ha="center", va="center",
                    color="white" if mat[i][j] < 0.5 else "black")
    plt.colorbar(im, ax=ax, label="F1")
    ax.set_title("Phase 10e: cross-language F1 transfer (combined-risk threshold)")
    plt.tight_layout()
    Path("figures").mkdir(exist_ok=True)
    plt.savefig("figures/phase10_cross_language.png", dpi=150)
    plt.close()
    print("\nwrote figures/phase10_cross_language.png")


if __name__ == "__main__":
    main()
