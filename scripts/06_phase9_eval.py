#!/usr/bin/env python3
"""Phase 9: SpecGuard detector evaluation against admitted triples.

For each admitted triple (review_passed=True, validation_failed=False) runs
all 5 detectors twice:
  - trojan input: triple as-is (positive: detectors *should* flag it)
  - honest input: triple with trojan_spec swapped for original_spec
                  (negative control: detectors *should* return CLEAN)

Streams per-triple per-set per-detector results to ``--results-jsonl`` line
by line so the run is resumable on interruption: already-evaluated triple_ids
(present in the file) are skipped on restart.

Concurrency: ThreadPoolExecutor across triples (network-bound through the
monitor-consensus detector, which internally runs 3 Bedrock monitors in
parallel via asyncio per scan).

Stop guards (per the Phase 9 plan):
  - detector errors > 10% of evaluated triples (>=50 done)
  - monitor responses > 20% malformed (>=60 monitor calls done)
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm

from trojanspec.specguard import scan_triple


def _admitted_triples(data_dirs: list[str]):
    for d in data_dirs:
        root = Path(d)
        if not root.exists():
            continue
        for f in root.rglob("*.json"):
            if f.name.endswith("_SUMMARY.json"):
                continue
            try:
                t = json.loads(f.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if t.get("review_passed") and not t.get("validation_failed"):
                yield t


def _eval_one(triple: dict, include_monitor: bool) -> dict:
    """Run scan_triple on the trojan and on its honest control."""
    trojan_report = scan_triple(triple, include_monitor=include_monitor)
    honest_triple = dict(triple)
    honest_triple["trojan_spec"] = triple.get("original_spec", "")
    honest_report = scan_triple(honest_triple, include_monitor=include_monitor)
    return {
        "triple_id": triple.get("triple_id"),
        "language": triple.get("language"),
        "attack_pattern": triple.get("attack_pattern"),
        "elicitor_model": triple.get("elicitor_model"),
        "source_benchmark": triple.get("source_benchmark"),
        "crypto_primitive": triple.get("crypto_primitive"),
        "trojan": trojan_report,
        "honest": honest_report,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--data-dir", nargs="+",
        default=["data/triples", "data/triples_xfamily"],
    )
    ap.add_argument("--results-jsonl", default="data/phase9_results.jsonl")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument(
        "--no-monitor", action="store_true",
        help="skip LLM monitor (offline static-detectors only)",
    )
    ap.add_argument("--sample", type=int, default=0,
                    help="0 = all admitted triples")
    args = ap.parse_args()

    triples = list(_admitted_triples(args.data_dir))
    if args.sample and len(triples) > args.sample:
        triples = triples[: args.sample]

    out = Path(args.results_jsonl)
    out.parent.mkdir(parents=True, exist_ok=True)
    done_ids: set[str] = set()
    if out.exists():
        for line in out.read_text().splitlines():
            try:
                done_ids.add(json.loads(line)["triple_id"])
            except (json.JSONDecodeError, KeyError):
                pass

    pending = [t for t in triples if t.get("triple_id") not in done_ids]
    print(
        f"admitted={len(triples)} already_done={len(done_ids)} "
        f"pending={len(pending)} concurrency={args.concurrency} "
        f"monitor={'OFF' if args.no_monitor else 'ON'}"
    )
    if not pending:
        print("PHASE9_EVAL_DONE (nothing to do)")
        return 0

    errors = 0
    monitor_calls = 0
    monitor_malformed = 0
    done = 0
    stopped = False
    with out.open("a") as fout, ThreadPoolExecutor(
        max_workers=args.concurrency
    ) as ex:
        futs = {ex.submit(_eval_one, t, not args.no_monitor): t for t in pending}
        for fut in tqdm(as_completed(futs), total=len(futs), desc="phase9"):
            t = futs[fut]
            try:
                rec = fut.result()
            except Exception as exc:  # noqa: BLE001 - one bad triple must not abort
                errors += 1
                rec = {"triple_id": t.get("triple_id"), "error": str(exc)}
            done += 1
            for side in ("trojan", "honest"):
                report = rec.get(side) if isinstance(rec, dict) else None
                if not isinstance(report, dict):
                    continue
                for d in report.get("detectors", []):
                    if d.get("detector") != "monitor_consensus":
                        continue
                    pm = d.get("detail", {}).get("per_monitor", {})
                    for vote in pm.values():
                        monitor_calls += 1
                        if vote == "abstain":
                            monitor_malformed += 1
            fout.write(json.dumps(rec) + "\n")
            fout.flush()
            if done >= 50 and errors / done > 0.10:
                print(f"\nSTOP: detector errors > 10% ({errors}/{done})")
                stopped = True
                break
            if monitor_calls >= 60 and monitor_malformed / monitor_calls > 0.20:
                print(
                    f"\nSTOP: monitor malformed > 20% "
                    f"({monitor_malformed}/{monitor_calls})"
                )
                stopped = True
                break
    if stopped:
        return 2
    print(
        f"PHASE9_EVAL_DONE pending={len(pending)} errors={errors} "
        f"monitor_malformed={monitor_malformed}/{monitor_calls}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
