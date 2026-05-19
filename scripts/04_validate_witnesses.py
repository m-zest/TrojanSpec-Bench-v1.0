#!/usr/bin/env python3
"""Phase 7: verifier validation, the sole admission filter (no human review).

For every generated triple (main benchmark and the cross-family ablation):

  * ``trojan_spec   + trojan_witness`` -> verifier must ACCEPT
  * ``original_spec + trojan_witness`` -> verifier must REJECT

A triple passing both is admitted and stamped
``reviewed_by = "auto-phase7-validator"``, ``review_passed = True``. A triple
failing either check is kept in the raw dataset with ``validation_failed =
True`` (transparency) but excluded from the admitted set.

Parallelism: ``--concurrency N`` (1..8) runs verification in a
``ProcessPoolExecutor`` - Lean/Dafny/Verus are CPU-bound external processes,
and ``verify_lean`` already copies the Mathlib template into a fresh tempdir
per call, so every worker process is fully isolated (no shared state).
``--skip-already-validated`` skips re-verifying any triple whose JSON already
has a ``validation_timestamp`` (its stored verdict is still counted toward the
report, so resuming an interrupted run yields a correct full-set admission).

Usage:
    python scripts/04_validate_witnesses.py
    python scripts/04_validate_witnesses.py --concurrency 4 --skip-already-validated
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm

from trojanspec.generators.validator import validate_triple
from trojanspec.schemas import Triple
from trojanspec.utils.logging import get_logger

log = get_logger("validate")

AUTO_REVIEWER = "auto-phase7-validator"


def _verdict(t: Triple) -> tuple[bool, str, str, str]:
    """(passed, language, attack, model) for report tallying."""
    passed = (
        t.verifier_accepts_witness_under_trojan
        and t.verifier_rejects_witness_under_original
    )
    return passed, t.language.value, t.attack_pattern.value, t.elicitor_model.split("/")[-1]


def _validate_file(path_str: str, timeout_sec: int) -> tuple[str, bool, str, str, str]:
    """Worker: verify one triple file, stamp + persist it, return its verdict.

    Top-level (picklable) so it runs under ProcessPoolExecutor. Each worker
    process inherits PATH / TROJANSPEC_LEAN_TEMPLATE; ``verify_lean`` copies
    the template into its own tempdir per call, so workers never share a Lean
    environment.
    """
    f = Path(path_str)
    t = Triple.model_validate_json(f.read_text())
    t = validate_triple(t, timeout_sec=timeout_sec)
    passed, lang, attack, model = _verdict(t)
    if passed:
        t.reviewed_by = AUTO_REVIEWER
        t.review_passed = True
        t.validation_failed = False
    else:
        t.review_passed = False
        t.validation_failed = True
    f.write_text(t.model_dump_json(indent=2))
    return path_str, passed, lang, attack, model


def _rate_table(title: str, counts: dict[str, list[int]]) -> None:
    print(f"\n{title}")
    for key in sorted(counts):
        adm, tot = counts[key]
        pct = (100 * adm / tot) if tot else 0.0
        print(f"  {key:24s} {adm:5d}/{tot:<5d}  {pct:5.1f}%")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--data-dir",
        nargs="+",
        default=["data/triples", "data/triples_xfamily"],
        help="one or more roots to validate",
    )
    ap.add_argument("--sample", type=int, default=0, help="0 = all triples")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="parallel verifier workers (1..8); 1 = sequential",
    )
    ap.add_argument(
        "--skip-already-validated",
        action="store_true",
        help="do not re-verify triples whose JSON has validation_timestamp "
        "(their stored verdict is still counted toward the report)",
    )
    ap.add_argument(
        "--report-json",
        default=None,
        help="also write the admission report to this JSON path",
    )
    args = ap.parse_args()
    concurrency = max(1, min(8, args.concurrency))

    files: list[Path] = []
    for d in args.data_dir:
        root = Path(d)
        if root.exists():
            files += [
                f for f in root.rglob("*.json") if not f.name.endswith("_SUMMARY.json")
            ]
        else:
            log.warning("data dir %s does not exist - skipping", d)

    if args.sample and len(files) > args.sample:
        files = random.sample(files, args.sample)

    by_lang: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    by_attack: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    by_model: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    admitted = 0

    def _tally(passed: bool, lang: str, attack: str, model: str) -> None:
        nonlocal admitted
        if passed:
            admitted += 1
        for tbl, k in ((by_lang, lang), (by_attack, attack), (by_model, model)):
            tbl[k][1] += 1
            if passed:
                tbl[k][0] += 1

    # Partition: already-validated (skip+tally stored verdict) vs to-verify.
    to_verify: list[Path] = []
    skipped = 0
    for f in files:
        if args.skip_already_validated:
            try:
                raw = json.loads(f.read_text())
            except (json.JSONDecodeError, OSError):
                to_verify.append(f)
                continue
            if raw.get("validation_timestamp"):
                t = Triple.model_validate(raw)
                _tally(*_verdict(t))
                skipped += 1
                continue
        to_verify.append(f)

    total = len(files)
    if args.skip_already_validated:
        log.info(
            "Skipping already validated: %d / %d (verifying remaining %d)",
            skipped,
            total,
            len(to_verify),
        )

    if concurrency == 1:
        for f in tqdm(to_verify, desc="validating"):
            _, passed, lang, attack, model = _validate_file(str(f), args.timeout)
            _tally(passed, lang, attack, model)
    else:
        with ProcessPoolExecutor(max_workers=concurrency) as ex:
            futures = {
                ex.submit(_validate_file, str(f), args.timeout): f for f in to_verify
            }
            for fut in tqdm(
                as_completed(futures), total=len(futures), desc="validating"
            ):
                try:
                    _, passed, lang, attack, model = fut.result()
                except Exception as exc:  # noqa: BLE001 - one bad triple must not abort
                    log.warning("validation worker failed for %s: %s", futures[fut], exc)
                    continue
                _tally(passed, lang, attack, model)

    pct = (100 * admitted / total) if total else 0.0
    log.info("Admitted %d / %d triples (%.1f%%)", admitted, total, pct)
    _rate_table("Admission rate by language:", by_lang)
    _rate_table("Admission rate by attack:", by_attack)
    _rate_table("Admission rate by model:", by_model)
    print(f"\nTOTAL ADMITTED: {admitted} / {total}  ({pct:.1f}%)")

    if args.report_json:
        def _tbl(c: dict[str, list[int]]) -> dict:
            return {
                k: {"admitted": v[0], "total": v[1],
                    "pct": round(100 * v[0] / v[1], 1) if v[1] else 0.0}
                for k, v in c.items()
            }

        report = {
            "total": total,
            "admitted": admitted,
            "admission_pct": round(pct, 1),
            "by_language": _tbl(by_lang),
            "by_attack": _tbl(by_attack),
            "by_model": _tbl(by_model),
        }
        Path(args.report_json).write_text(json.dumps(report, indent=2))
        print(f"\nadmission report -> {args.report_json}")


if __name__ == "__main__":
    main()
