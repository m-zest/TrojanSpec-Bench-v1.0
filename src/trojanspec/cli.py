"""``trojanspec`` CLI: inspect the schema, registry, and dataset stats.

Generation / review / validation are heavyweight stages with their own
numbered scripts under ``scripts/``; this CLI is for quick introspection.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from trojanspec import __version__
from trojanspec.crypto import ANCHORS
from trojanspec.schemas import Triple
from trojanspec.utils.llm_clients import available_families


def _cmd_schema(_: argparse.Namespace) -> int:
    print(json.dumps(Triple.model_json_schema(), indent=2))
    return 0


def _cmd_backends(_: argparse.Namespace) -> int:
    print("Available LLM families:")
    for fam in available_families():
        print(f"  - {fam}")
    return 0


def _cmd_anchors(_: argparse.Namespace) -> int:
    print(f"{len(ANCHORS)} cryptographic anchors registered:")
    for (prim, atk, lang), anchor in sorted(
        ANCHORS.items(), key=lambda kv: (kv[0][0].value, kv[0][1].value, kv[0][2].value)
    ):
        print(f"  {prim.value:14s} {atk.value:22s} {lang.value:6s}  <- {anchor.bug_source}")
    return 0


def _cmd_stats(args: argparse.Namespace) -> int:
    data_dir = Path(args.data_dir)
    files = list(data_dir.rglob("*.json"))
    total = len(files)
    admitted = 0
    for f in files:
        try:
            t = Triple.model_validate_json(f.read_text())
        except Exception:  # noqa: BLE001 - skip unparseable
            continue
        admitted += int(t.is_admitted)
    print(f"data dir : {data_dir}")
    print(f"triples  : {total}")
    print(f"admitted : {admitted}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trojanspec", description=__doc__)
    parser.add_argument("--version", action="version", version=f"trojanspec {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("schema", help="print the Triple JSON schema").set_defaults(
        func=_cmd_schema
    )
    sub.add_parser("backends", help="list available LLM families").set_defaults(
        func=_cmd_backends
    )
    sub.add_parser("anchors", help="list registered crypto anchors").set_defaults(
        func=_cmd_anchors
    )
    stats = sub.add_parser("stats", help="dataset admission statistics")
    stats.add_argument("--data-dir", default="data/triples")
    stats.set_defaults(func=_cmd_stats)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
