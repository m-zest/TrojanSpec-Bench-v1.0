#!/usr/bin/env python3
"""SpecGuard CLI: run the five detectors over a triple JSON.

    python scripts/05_specguard.py path/to/triple.json [--no-monitor] [--quiet]

Prints a JSON report: per-detector verdict (clean / suspicious / malicious)
plus an overall verdict and a 0-1 combined risk score. Exit code is 0 for a
clean triple, 1 if SpecGuard flags it (suspicious or malicious).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trojanspec.specguard import scan_triple


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("triple", type=Path, help="path to a triple JSON file")
    ap.add_argument(
        "--no-monitor",
        action="store_true",
        help="skip the LLM monitor-consensus detector (offline / fast)",
    )
    ap.add_argument("--quiet", action="store_true", help="print only the verdict line")
    args = ap.parse_args()

    triple = json.loads(args.triple.read_text())
    report = scan_triple(triple, include_monitor=not args.no_monitor)

    if args.quiet:
        print(f"{report['overall_verdict']}  risk={report['risk_score']}")
    else:
        print(json.dumps(report, indent=2))

    return 0 if report["overall_verdict"] == "clean" else 1


if __name__ == "__main__":
    sys.exit(main())
