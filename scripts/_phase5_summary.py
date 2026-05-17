#!/usr/bin/env python3
"""Write a per-phase generation manifest.

    python scripts/_phase5_summary.py <out_dir> <phase> <expected>

Scans every Triple JSON under ``out_dir`` and writes
``<out_dir>/<phase>_SUMMARY.json`` with yield, per-facet counts and a rough
token/cost estimate. The raw triples are git-ignored; this manifest is the
committed, reproducible record of the run.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

# Rough Fireworks blended price (USD per 1M tokens); approximate, for an
# order-of-magnitude cost figure only.
_USD_PER_MTOK = 0.90


def main() -> None:
    out_dir = Path(sys.argv[1])
    phase = sys.argv[2]
    expected = int(sys.argv[3])

    files = sorted(out_dir.rglob("*.json"))
    files = [f for f in files if not f.name.endswith("_SUMMARY.json")]
    lang: Counter = Counter()
    attack: Counter = Counter()
    model: Counter = Counter()
    approx_tokens = 0
    for f in files:
        t = json.loads(f.read_text())
        lang[t["language"]] += 1
        attack[t["attack_pattern"]] += 1
        model[t["elicitor_model"].split("/")[-1]] += 1
        approx_tokens += len(t.get("elicitor_response_full", "")) // 4 + 1800

    n = len(files)
    summary = {
        "phase": phase,
        "expected": expected,
        "generated": n,
        "yield_pct": round(100 * n / expected, 1) if expected else 0.0,
        "per_language": dict(lang),
        "per_attack": dict(attack),
        "per_model": dict(model),
        "approx_total_tokens": approx_tokens,
        "approx_cost_usd": round(approx_tokens / 1_000_000 * _USD_PER_MTOK, 4),
        "note": (
            "Raw triples are git-ignored (regenerated locally); this manifest "
            "is the committed record. Cost is a rough blended estimate."
        ),
    }
    out = out_dir / f"{phase}_SUMMARY.json"
    out.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
