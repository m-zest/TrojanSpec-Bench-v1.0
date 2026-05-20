"""Phase 14 step 3: extract the 319 admitted Dafny triple pairs as standalone
.dfy files that MutDafny (Amaral, Mendes, Campos — arXiv:2511.15403, ICSE 2026)
can ingest. Writes <triple_id>.honest.dfy and <triple_id>.trojan.dfy per triple.

Composition uses the same code path Phase 7 used to admit them
(``trojanspec.verifiers.compose.compose``), so a .dfy that verifies under
Dafny 4.11 in Phase 7 will verify under MutDafny's bundled Dafny 4.10.1 fork
in Step 4 (verified empirically: 5/5 sanity-pair pass rate).
"""
from __future__ import annotations

import argparse
import glob
import json
import random
import sys
import tarfile
import tempfile
from pathlib import Path

from trojanspec.schemas import Language
from trojanspec.verifiers.compose import compose


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--tarball",
        default="data/v4_backup_20260519_224805.tar.gz",
        help="v4 backup tarball with raw triple JSONs",
    )
    ap.add_argument(
        "--phase9",
        default="data/phase9_results_v2.jsonl",
        help="Phase 9 v2 results — filter to language==dafny gives the 319 admitted IDs",
    )
    ap.add_argument(
        "--out-dir",
        default="/tmp/mutdafny_inputs",
        help="Directory for the 638 .dfy files",
    )
    ap.add_argument(
        "--sanity-n",
        type=int,
        default=5,
        help="How many random pairs to print for sanity verification",
    )
    ap.add_argument("--sanity-seed", type=int, default=2026)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. extract tarball into a temp dir, index by triple_id
    with tempfile.TemporaryDirectory() as td:
        with tarfile.open(args.tarball, "r:gz") as tar:
            tar.extractall(td)
        idx: dict[str, dict] = {}
        for p in glob.glob(f"{td}/**/*.json", recursive=True):
            try:
                t = json.load(open(p))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(t, dict) and "triple_id" in t:
                idx[t["triple_id"]] = t
        print(f"extracted {len(idx)} raw triples from {args.tarball}")

        # 2. filter to admitted Dafny
        admitted = [
            json.loads(line)["triple_id"]
            for line in open(args.phase9)
            if json.loads(line).get("language") == "dafny"
        ]
        print(f"admitted dafny triples in {args.phase9}: {len(admitted)}")

        missing = [tid for tid in admitted if tid not in idx]
        if missing:
            sys.stderr.write(f"ERROR: {len(missing)} admitted IDs not found in tarball\n")
            sys.exit(2)

        # 3. compose
        for tid in admitted:
            t = idx[tid]
            preamble = t.get("preamble") or ""
            honest = compose(preamble, t["original_spec"], t["original_spec"], Language.DAFNY)
            trojan = compose(preamble, t["trojan_spec"], t["trojan_witness"], Language.DAFNY)
            (out_dir / f"{tid}.honest.dfy").write_text(honest)
            (out_dir / f"{tid}.trojan.dfy").write_text(trojan)
        print(f"wrote {2 * len(admitted)} .dfy files to {out_dir}")

    # 4. print sanity-pair IDs for the operator to verify
    random.seed(args.sanity_seed)
    sample = random.sample(admitted, min(args.sanity_n, len(admitted)))
    print(f"\nsanity sample (seed={args.sanity_seed}, n={len(sample)}):")
    for tid in sample:
        print(f"  {tid}")
    print("\nverify each with:")
    print(
        "  dotnet ~/tools/mutdafny/dafny/Binaries/Dafny.dll verify "
        f"{out_dir}/<tid>.honest.dfy --solver-path ~/tools/mutdafny/dafny/Binaries/z3 "
        "--allow-warnings"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
