"""Build the Phase 11 Mathlib case study report from
data/phase11_results.jsonl + data/phase11_summary.json.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def main() -> None:
    summary = json.loads(Path("data/phase11_summary.json").read_text())
    records = []
    for ln in Path("data/phase11_results.jsonl").read_text().splitlines():
        if ln.strip():
            records.append(json.loads(ln))

    # axiom_audit findings: list which lemmas tripped it and on what construct
    ax_hits = []
    for r in records:
        ax = r["axiom_audit"]
        if ax["verdict"] != "clean":
            constructs = ax.get("detail", {}).get("new_constructs", [])
            ax_hits.append((r["name"], constructs[:3], r["source_file"]))

    # monitor_consensus findings: lemmas the 3 monitors collectively flagged
    mc_hits = []
    for r in records:
        mc = r["monitor_consensus"]
        if mc["verdict"] != "clean":
            mc_hits.append((r["name"], mc.get("per_monitor", {}), r["source_file"]))

    # Top source files in the sample
    top_files = Counter(r["source_file"] for r in records).most_common(10)

    md: list[str] = []
    md.append("# Phase 11 — Mathlib case study\n")
    md.append(f"Applied `axiom_audit` (post-fix, multi-language) and "
              f"`monitor_consensus` (3 Bedrock monitors) to **{summary['n_theorems']}** "
              "Lean theorems sampled from the project's Mathlib snapshot at "
              "`$TROJANSPEC_LEAN_TEMPLATE/.lake/packages/mathlib/Mathlib`. "
              "No attack here - this is a calibration baseline that says how "
              "SpecGuard rates *real, honest* formal mathematics.\n")
    md.append("## Headline\n")
    md.append("| detector | flagged | rate | what this means |")
    md.append("|---|---:|---:|---|")
    md.append(f"| `axiom_audit` | {summary['axiom_audit_flagged']}/{summary['n_theorems']} "
              f"| {summary['axiom_audit_flag_rate']:.3f} | rate at which our "
              "unverified-surface patterns match real Mathlib lemmas (a Mathlib "
              "lemma that legitimately uses `axiom`/`opaque` will fire `axiom_audit`). |")
    md.append(f"| `monitor_consensus` | {summary['monitor_consensus_flagged']}/{summary['n_theorems']} "
              f"| {summary['monitor_consensus_flag_rate']:.3f} | rate at which a "
              "majority of 3 Bedrock monitors judges a real Mathlib lemma "
              "UNFAITHFUL given the lemma's identifier as the NL hint. This is "
              "the LLM-as-judge FPR upper bound on a known-honest corpus. |")
    md.append(f"\n{summary['interpretation']}\n")

    md.append("## `axiom_audit` hits (first 20)\n")
    md.append("| lemma | new_constructs | source |")
    md.append("|---|---|---|")
    for name, constructs, src in ax_hits[:20]:
        md.append(f"| `{name}` | `{', '.join(constructs)}` | `{src}` |")
    if len(ax_hits) > 20:
        md.append(f"\n…and {len(ax_hits) - 20} more.\n")

    md.append("\n## `monitor_consensus` hits (first 20)\n")
    md.append("| lemma | per-monitor votes | source |")
    md.append("|---|---|---|")
    for name, per_mon, src in mc_hits[:20]:
        vstr = ", ".join(f"{k.split('-')[-1]}={v}" for k, v in per_mon.items())
        md.append(f"| `{name}` | {vstr} | `{src}` |")
    if len(mc_hits) > 20:
        md.append(f"\n…and {len(mc_hits) - 20} more.\n")

    md.append("\n## Sampled source files (top 10 by lemma count)\n")
    md.append("| file | n_lemmas_sampled |")
    md.append("|---|---:|")
    for f, n in top_files:
        md.append(f"| `{f}` | {n} |")
    md.append("")

    Path("docs/phase11_mathlib_case_study.md").write_text("\n".join(md))
    print("wrote docs/phase11_mathlib_case_study.md")
    print(f"axiom_audit hits: {len(ax_hits)}/{summary['n_theorems']}")
    print(f"monitor_consensus hits: {len(mc_hits)}/{summary['n_theorems']}")


if __name__ == "__main__":
    main()
