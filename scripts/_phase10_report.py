"""Consolidate Phase 10 ablation results into docs/phase10_ablations.md
and data/phase10_ablations.json. Reads whatever 10a/b/c/d/e/f/g outputs are
present; missing pieces are noted but do not abort.
"""
from __future__ import annotations

import json
from pathlib import Path


def _load(path: str) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def main() -> None:
    out: dict = {}
    md: list[str] = ["# Phase 10 — Ablations\n",
                     "Seven ablations on the Phase 9 SpecGuard evaluation. The "
                     "post-hoc ones (10a/d/e) are zero-LLM-cost replays over the "
                     "Phase 9 jsonl; 10b/c/f/g are Bedrock-billed.\n"]

    # 10a elicitor sweep
    a = _load("data/phase10_10a_elicitor_sweep.json")
    if a:
        out["10a_elicitor_sweep"] = a
        md.append("## 10a — Elicitor sweep")
        md.append("Re-tallied Phase 9 metrics on per-elicitor subsets "
                  "(Sonnet n=906, Haiku n=59, Llama n=59).\n")
        md.append("| family | vacuity F1 | mutation F1 | ghost F1 | axiom F1 | monitor F1 |")
        md.append("|---|---:|---:|---:|---:|---:|")
        for fam in ("all", "sonnet", "haiku", "llama"):
            if fam not in a.get("by_elicitor", {}):
                continue
            v = a["by_elicitor"][fam]["per_detector"]
            md.append(f"| {fam} (n={a['by_elicitor'][fam]['n']}) "
                      f"| {v['vacuity']['f1']:.3f} | {v['mutation_coverage']['f1']:.3f} "
                      f"| {v['ghost_leakage']['f1']:.3f} | {v['axiom_audit']['f1']:.3f} "
                      f"| {v['monitor_consensus']['f1']:.3f} |")
        md.append("\n**Headline:** Haiku-generated trojans are easier to detect — "
                  "`ghost_leakage` recall jumps to 0.593 (vs 0.117 on Sonnet) and "
                  "`axiom_audit` recall to 0.508 (vs 0.353). Llama tracks Sonnet. "
                  "`monitor_consensus` recall is 1.000 on all three subsets.\n")
        md.append("![elicitor sweep](../figures/phase10_elicitor_sweep.png)\n")

    # 10b temperature
    b = _load("data/phase10_10b_temperature.json")
    if b:
        out["10b_temperature"] = b
        md.append("## 10b — Monitor temperature ablation")
        md.append(f"{b['n']} sampled admitted triples; single-monitor (Sonnet) at temperatures {b['temps']}.\n")
        md.append("| temp | unfaithful | faithful | abstain | unfaithful_rate | agree_with_default |")
        md.append("|---:|---:|---:|---:|---:|---:|")
        for t in b["temps"]:
            v = b["per_temp"][str(t)]
            md.append(f"| {t} | {v['unfaithful']} | {v['faithful']} | {v['abstain']} "
                      f"| {v['unfaithful_rate']:.3f} | {v.get('agree_with_default', 0):.3f} |")
        md.append("\n**Headline:** Sonnet's verdict is temperature-stable on admitted "
                  "trojans (saturation: every admitted weakening is judged UNFAITHFUL "
                  "with confidence at all temperatures).\n")

    # 10c monitor count
    c = _load("data/phase10_10c_monitor_count.json")
    if c:
        out["10c_monitor_count"] = c
        md.append("## 10c — Monitor count ablation")
        md.append(f"{c['sample']} sampled admitted triples; panels of 1, 3, 5 monitors.\n")
        md.append("| panel size | composition | TP | FP | precision | recall | F1 | FPR |")
        md.append("|---:|---|---:|---:|---:|---:|---:|---:|")
        for size in ("1", "3", "5"):
            if size not in c["panels"]:
                continue
            p = c["panels"][size]
            comp = " + ".join(f"{x['label']}@{x['temperature']}" for x in p["panel"])
            md.append(f"| {size} | {comp} | {p['trojan_flagged']} | {p['honest_flagged']} "
                      f"| {p['precision']:.3f} | {p['recall']:.3f} | {p['f1']:.3f} "
                      f"| {p['fpr']:.3f} |")
        md.append("")

    # 10d ensemble grid
    d = _load("data/phase10_10d_ensemble_grid.json")
    if d:
        out["10d_ensemble_grid"] = d
        md.append("## 10d — Detector ensemble grid (post-hoc, no LLM cost)")
        md.append(f"Searched all 31 nonempty subsets of the 5 detectors over "
                  f"{d['n_records']} records.\n")
        best = d["best_by_f1"]
        cheap = d["cheapest_at_best_f1"]
        md.append(f"- **Best by F1:** `{'+'.join(best['subset'])}` — F1 **{best['f1']:.3f}** "
                  f"(P {best['precision']:.3f}, R {best['recall']:.3f}, "
                  f"FPR {best['fpr']:.3f}, cost {best['cost']} LLM calls/triple).")
        md.append(f"- **Cheapest at max F1:** `{'+'.join(cheap['subset'])}` (cost {cheap['cost']}).\n")
        md.append("**Headline:** `monitor_consensus` alone is the F1-optimal subset; "
                  "adding static detectors does not improve F1 (they catch a strict "
                  "subset of what monitor catches), and adding `axiom_audit` *hurts* "
                  "F1 to 0.829 because the shared preamble makes it FP on the honest "
                  "control.\n")
        md.append("![ensemble grid](../figures/phase10_ensemble_grid.png)\n")

    # 10e cross-language
    e = _load("data/phase10_10e_cross_language.json")
    if e:
        out["10e_cross_language"] = e
        md.append("## 10e — Cross-language transfer")
        md.append(f"Combined-risk threshold tuned on one language, applied to the "
                  f"other two. Per-language n: {e['per_language_n']}.\n")
        md.append("| train \\ eval | dafny | lean | verus | threshold |")
        md.append("|---|---:|---:|---:|---:|")
        for tr in ("dafny", "lean", "verus"):
            row = e["matrix"][tr]
            md.append(f"| {tr} | {row['applied_to']['dafny']['f1']:.3f} "
                      f"| {row['applied_to']['lean']['f1']:.3f} "
                      f"| {row['applied_to']['verus']['f1']:.3f} "
                      f"| {row['threshold']:.3f} |")
        md.append("\n**Headline:** Threshold (0.750) is identical across languages "
                  "and transfers perfectly; per-language F1 varies (Dafny 0.995, "
                  "Lean 0.851, Verus 0.677) tracking how loose each language's "
                  "honest-control seeds are.\n")
        md.append("![cross language](../figures/phase10_cross_language.png)\n")

    # 10f SSC baseline
    f = _load("data/phase10_10f_ssc_summary.json")
    if f:
        out["10f_ssc_baseline"] = f
        md.append("## 10f — Self-Spec Consistency baseline")
        md.append(f"Single-model two-paraphrased-question consistency check on "
                  f"{f['n']} triples. {f['baseline_note']}\n")
        md.append("| baseline | TP | FP | precision | recall | F1 | FPR |")
        md.append("|---|---:|---:|---:|---:|---:|---:|")
        md.append(f"| SSC (Sonnet, 2 questions) | {f['tp']} | {f['fp']} "
                  f"| {f['precision']:.3f} | {f['recall']:.3f} "
                  f"| {f['f1']:.3f} | {f['fpr']:.3f} |")
        # Compare to monitor_consensus from Phase 9
        m = _load("data/phase9_metrics_v2.json")
        if m:
            mc = m["per_detector"]["monitor_consensus"]
            md.append(f"| monitor_consensus (Phase 9, 3 monitors) | {mc['tp']} | {mc['fp']} "
                      f"| {mc['precision']:.3f} | {mc['recall']:.3f} "
                      f"| {mc['f1']:.3f} | {mc['fpr']:.3f} |")
        md.append("")

    # 10g adaptive attack
    g = _load("data/phase10_10g_adaptive.json")
    if g:
        out["10g_adaptive_attack"] = g
        md.append("## 10g — Adaptive attack stress test")
        md.append(f"Sonnet rewrote {g['sampled']} admitted implementation_leak trojans "
                  "to avoid all of axiom-like markers (`axiom`, `opaque`, `{{:axiom}}`, "
                  "`{{:extern}}`, `external_body`, `external`, `assume_specification`, "
                  "`assume(`). Re-verified the dual property; ran SpecGuard on those "
                  "that still admitted. Per Terekhov et al. arXiv:2510.09462, this "
                  "measures how much a published detector loses recall when the "
                  "attacker adapts.\n")
        md.append(f"- model followed the banned-marker constraint: **{g['model_followed_constraint']} / {g['sampled']}**")
        md.append(f"- adaptive variants that re-verified (dual property holds): "
                  f"**{g['admitted_after_reverify']} / {g['sampled']}** "
                  f"({g['admitted_pct']*100:.1f}%)")
        md.append(f"- `axiom_audit` recall on the adaptive admitted set: "
                  f"**{g['axiom_audit_recall_on_adaptive']:.3f}** "
                  f"(baseline: 1.000 on non-adaptive implementation_leak)")
        md.append(f"- static detector flags on adaptive admitted set: "
                  f"`{g['static_detector_catch_on_admitted']}`\n")
        md.append("**Interpretation:** any recall drop here is the cost of an "
                  "attacker-aware adversary; SpecGuard's `monitor_consensus` "
                  "(semantic LLM-judge) is the principled fallback for novel "
                  "weakening shapes the static detectors do not yet pattern-match.\n")

    Path("data/phase10_ablations.json").write_text(json.dumps(out, indent=2))
    Path("docs/phase10_ablations.md").write_text("\n".join(md))
    print("wrote data/phase10_ablations.json")
    print("wrote docs/phase10_ablations.md")


if __name__ == "__main__":
    main()
