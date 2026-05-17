#!/usr/bin/env python3
"""Generate TrojanSpec triples end-to-end.

Each source problem is attacked with all four patterns, rotating across LLM
families for cross-family diversity. Outputs land in
``data/triples/<lang>/<difficulty>/<triple_id>.json``.

Usage:
    python scripts/02_generate_triples.py --per-cell 100 --concurrency 8
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from tqdm import tqdm

from trojanspec.generators.elicitor import elicit_triple
from trojanspec.loaders import load_all_source_problems
from trojanspec.schemas import AttackPattern, Language
from trojanspec.utils.llm_clients import available_families, get_client
from trojanspec.utils.logging import get_logger

log = get_logger("generate")

DEFAULT_FAMILIES = ["openrouter-llama", "ollama-qwen", "openrouter-claude"]


async def _one(problem, attack, family, temperature):
    client = get_client(family, temperature=temperature)
    return await elicit_triple(
        client=client, problem=problem, attack_pattern=attack, temperature=temperature
    )


async def run(per_cell: int, concurrency: int, families: list[str], temperature: float):
    out_root = Path("data/triples")
    out_root.mkdir(parents=True, exist_ok=True)
    problems = load_all_source_problems()

    jobs = []
    for lang in Language:
        cell = problems.get((lang, "all"), [])[:per_cell]
        for attack in AttackPattern:
            for i, prob in enumerate(cell):
                fam = families[i % len(families)]
                jobs.append((prob, attack, fam))

    if not jobs:
        log.warning("No source problems found - nothing to generate.")
        return

    sem = asyncio.Semaphore(concurrency)
    ok = 0

    async def bounded(prob, attack, fam):
        nonlocal ok
        async with sem:
            try:
                triple = await _one(prob, attack, fam, temperature)
            except Exception as exc:  # noqa: BLE001 - log and continue the batch
                log.warning("generation failed (%s/%s): %s", attack.value, fam, exc)
                return
            d = out_root / triple.language.value / triple.difficulty.value
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{triple.triple_id}.json").write_text(triple.model_dump_json(indent=2))
            ok += 1

    tasks = [asyncio.create_task(bounded(p, a, f)) for p, a, f in jobs]
    for fut in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="eliciting"):
        await fut

    log.info("Generated %d / %d triples into %s", ok, len(jobs), out_root)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-cell", type=int, default=100)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument(
        "--families",
        nargs="+",
        default=DEFAULT_FAMILIES,
        help=f"LLM families to rotate. Available: {', '.join(available_families())}",
    )
    args = ap.parse_args()
    asyncio.run(
        run(args.per_cell, args.concurrency, args.families, args.temperature)
    )


if __name__ == "__main__":
    main()
