#!/usr/bin/env python3
"""Validate reviewer-accepted triples against the real verifiers.

Admission criterion (both required):
  * trojan_spec   + trojan_witness  -> verifier ACCEPTS
  * original_spec + trojan_witness  -> verifier REJECTS

Usage:
    python scripts/04_validate_witnesses.py [--sample N]
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from tqdm import tqdm

from trojanspec.generators.validator import validate_triple
from trojanspec.schemas import Triple
from trojanspec.utils.logging import get_logger

log = get_logger("validate")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", default="data/triples")
    ap.add_argument("--sample", type=int, default=0, help="0 = all reviewer-accepted")
    ap.add_argument("--timeout", type=int, default=60)
    args = ap.parse_args()

    files = list(Path(args.data_dir).rglob("*.json"))
    candidates = []
    for f in files:
        t = Triple.model_validate_json(f.read_text())
        if t.review_passed:
            candidates.append((f, t))

    if args.sample and len(candidates) > args.sample:
        candidates = random.sample(candidates, args.sample)

    admitted = 0
    for f, t in tqdm(candidates, desc="validating"):
        t = validate_triple(t, timeout_sec=args.timeout)
        if t.is_admitted:
            admitted += 1
        f.write_text(t.model_dump_json(indent=2))

    log.info(
        "Admitted %d / %d reviewer-accepted triples to TrojanSpec-Bench",
        admitted,
        len(candidates),
    )


if __name__ == "__main__":
    main()
