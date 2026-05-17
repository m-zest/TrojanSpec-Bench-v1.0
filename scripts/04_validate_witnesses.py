#!/usr/bin/env python3
"""Phase 7: verifier validation, the sole admission filter (no human review).

For every generated triple (main benchmark and the cross-family ablation):

  * ``trojan_spec   + trojan_witness`` -> verifier must ACCEPT
  * ``original_spec + trojan_witness`` -> verifier must REJECT

A triple passing both is admitted and stamped
``reviewed_by = "auto-phase7-validator"``, ``review_passed = True``. A triple
failing either check is kept in the raw dataset with ``validation_failed =
True`` (transparency) but excluded from the admitted set.

Usage:
    python scripts/04_validate_witnesses.py
    python scripts/04_validate_witnesses.py --data-dir data/triples --sample 100
"""

from __future__ import annotations

import argparse
import random
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm

from trojanspec.generators.validator import validate_triple
from trojanspec.schemas import Triple
from trojanspec.utils.logging import get_logger

log = get_logger("validate")

AUTO_REVIEWER = "auto-phase7-validator"


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
    args = ap.parse_args()

    files: list[Path] = []
    for d in args.data_dir:
        root = Path(d)
        if root.exists():
            files += [
                f for f in root.rglob("*.json") if not f.name.endswith("_SUMMARY.json")
            ]
        else:
            log.warning("data dir %s does not exist - skipping", d)

    candidates = [(f, Triple.model_validate_json(f.read_text())) for f in files]
    if args.sample and len(candidates) > args.sample:
        candidates = random.sample(candidates, args.sample)

    by_lang: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    by_attack: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    by_model: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    admitted = 0

    for f, t in tqdm(candidates, desc="validating"):
        t = validate_triple(t, timeout_sec=args.timeout)
        passed = (
            t.verifier_accepts_witness_under_trojan
            and t.verifier_rejects_witness_under_original
        )
        if passed:
            t.reviewed_by = AUTO_REVIEWER
            t.review_passed = True
            t.validation_failed = False
            admitted += 1
        else:
            t.review_passed = False
            t.validation_failed = True

        model = t.elicitor_model.split("/")[-1]
        for tbl, k in (
            (by_lang, t.language.value),
            (by_attack, t.attack_pattern.value),
            (by_model, model),
        ):
            tbl[k][1] += 1
            if passed:
                tbl[k][0] += 1

        f.write_text(t.model_dump_json(indent=2))

    total = len(candidates)
    pct = (100 * admitted / total) if total else 0.0
    log.info("Admitted %d / %d triples (%.1f%%)", admitted, total, pct)
    _rate_table("Admission rate by language:", by_lang)
    _rate_table("Admission rate by attack:", by_attack)
    _rate_table("Admission rate by model:", by_model)
    print(f"\nTOTAL ADMITTED: {admitted} / {total}  ({pct:.1f}%)")


if __name__ == "__main__":
    main()
