#!/usr/bin/env python3
"""Generate TrojanSpec triples end-to-end (Phase 5).

Backend: Fireworks AI only. Four independent model families are rotated with
equal (25 percent) weight for cross-family diversity:

    fireworks-gptoss   (OpenAI GPT-OSS 120B)
    fireworks-glm      (Zhipu GLM 5.1)
    fireworks-deepseek (DeepSeek v4 Pro)
    fireworks-kimi     (Moonshot Kimi K2.6)

Target: 1,500 triples = 3 languages x 4 attack patterns x 125 per cell.
Per (language, attack) cell the 125 split is 33 easy, 67 medium, 25 hard.
Hard triples are crypto-anchored: the source (nl, spec) is drawn from the
registered crypto anchors so the difficulty correlates with real disclosed
cryptographic bug shapes.

Retry-with-exponential-backoff (max 3 retries, base delay 2s, on HTTP 429 /
5xx / transport errors) is implemented in the Fireworks client itself, so it
applies to every call this script makes.

Usage:
    python scripts/02_generate_triples.py                 # full 1,500
    python scripts/02_generate_triples.py --sanity        # 10-triple test
    python scripts/02_generate_triples.py --per-cell 10   # smaller run
"""

from __future__ import annotations

import argparse
import asyncio
import itertools
import random
import time
from pathlib import Path

from tqdm import tqdm

from trojanspec.crypto import list_anchors
from trojanspec.crypto.anchor_registry import ANCHORS, get_anchor
from trojanspec.generators.elicitor import SourceProblem, elicit_triple
from trojanspec.loaders import load_all_source_problems
from trojanspec.schemas import (
    AttackPattern,
    CryptoPrimitive,
    Difficulty,
    Language,
    SourceBenchmark,
    Triple,
)
from trojanspec.utils.llm_clients import get_client
from trojanspec.utils.logging import get_logger

log = get_logger("generate")

# Primary backend: four Fireworks model families. GLM is the slowest
# (very long reasoning chains), so its weight is reduced to 10 percent while
# the other three keep 30 percent each: this preserves four-family diversity
# while removing GLM as the throughput bottleneck for the full run.
ELICITOR_FAMILIES = [
    "fireworks-gptoss",
    "fireworks-glm",
    "fireworks-deepseek",
    "fireworks-kimi",
]
FAMILY_WEIGHTS = {
    "fireworks-gptoss": 0.30,
    "fireworks-deepseek": 0.30,
    "fireworks-kimi": 0.30,
    "fireworks-glm": 0.10,
}

# Per-family max_tokens. Reasoning models need room for the thinking channel
# *and* the JSON answer; the values are tuned from a token-usage probe
# (completion tokens + finish_reason) against the real attack prompt.
DEFAULT_MAX_TOKENS = 8000
FAMILY_MAX_TOKENS = {
    "fireworks-kimi": 16000,    # Kimi reasoning is the most verbose (~6k probe)
    "fireworks-gptoss": 8000,   # probe: only ~1.2k tokens, 8k is ample headroom
    "fireworks-deepseek": 8000,
    "fireworks-glm": 8000,      # latency bounded via 10pc weight + 300s timeout
}

# Per (language, attack) cell difficulty split. Sums to 125; x 12 cells = 1500.
CELL_SPLIT = {Difficulty.EASY: 33, Difficulty.MEDIUM: 67, Difficulty.HARD: 25}
CONCURRENCY = 8


def _crypto_sources(language: Language) -> list[SourceProblem]:
    """Crypto-anchored seed problems for the HARD bucket of every cell.

    The anchor's honest (nl, original_spec) becomes the source problem; the
    LLM is then asked to trojan it under the cell's attack pattern in the
    cell's language, so the grid stays consistent while the seed is anchored
    to a real disclosed bug.
    """
    out: list[SourceProblem] = []
    for a in ANCHORS.values():
        out.append(
            SourceProblem(
                nl=a.nl_requirement,
                spec=a.original_spec,
                language=language,
                difficulty=Difficulty.HARD,
                source=SourceBenchmark.LIBCRUX_BUG,
                crypto=a.primitive,
            )
        )
    return out


def _bucket_sources(
    base: list[SourceProblem], language: Language, difficulty: Difficulty
) -> list[SourceProblem]:
    """Source problems re-stamped to a target difficulty bucket (cycled)."""
    if not base:
        return []
    return [
        SourceProblem(
            nl=p.nl,
            spec=p.spec,
            language=language,
            difficulty=difficulty,
            source=p.source,
            crypto=p.crypto,
        )
        for p in base
    ]


def weighted_family_sequence(n: int, *, seed: int = 1234) -> list[str]:
    """Exactly ``n`` family names matching FAMILY_WEIGHTS (largest remainder).

    Deterministic and shuffled, so the proportions hold even for short runs
    and the slow GLM family is spread out rather than clustered.
    """
    quotas = {f: FAMILY_WEIGHTS[f] * n for f in ELICITOR_FAMILIES}
    base = {f: int(q) for f, q in quotas.items()}
    remainder = n - sum(base.values())
    for f in sorted(quotas, key=lambda k: quotas[k] - base[k], reverse=True)[:remainder]:
        base[f] += 1
    seq = [f for f, c in base.items() for _ in range(c)]
    random.Random(seed).shuffle(seq)
    return seq


def _anchor_source(language: Language) -> list[SourceProblem]:
    """One SourceProblem per registered crypto anchor in ``language``."""
    return [
        SourceProblem(
            nl=a.nl_requirement,
            spec=a.original_spec,
            language=language,
            difficulty=Difficulty.HARD,
            source=SourceBenchmark.LIBCRUX_BUG,
            crypto=a.primitive,
        )
        for a in list_anchors(language=language)
    ]


def build_jobs(per_cell_split: dict[Difficulty, int]) -> list[tuple]:
    """One job = (SourceProblem, AttackPattern, family_name)."""
    problems = load_all_source_problems()
    jobs: list[tuple] = []

    for lang in Language:
        non_crypto = problems.get((lang, "all"), [])
        crypto = _crypto_sources(lang)
        for attack in AttackPattern:
            for difficulty, n in per_cell_split.items():
                if n == 0:
                    continue
                if difficulty is Difficulty.HARD:
                    pool = crypto or _bucket_sources(non_crypto, lang, difficulty)
                else:
                    pool = _bucket_sources(non_crypto, lang, difficulty)
                if not pool:
                    log.warning(
                        "no source problems for %s/%s/%s - skipping",
                        lang.value,
                        attack.value,
                        difficulty.value,
                    )
                    continue
                pool_cycle = itertools.cycle(pool)
                for _ in range(n):
                    jobs.append([next(pool_cycle), attack])
    fams = weighted_family_sequence(len(jobs))
    return [(p, a, f) for (p, a), f in zip(jobs, fams, strict=True)]


# Curated 10-anchor sanity selection: 4 Dafny + 3 Lean + 3 Verus, all four
# attack patterns present, and exactly two vacuity jobs on *different*
# languages (Dafny SHA-3 and Lean ML-KEM-1024). Attack mix: 2 vacuity,
# 2 domain_restriction, 3 predicate_swap, 3 implementation_leak.
_SANITY_KEYS = [
    (CryptoPrimitive.SHA3, AttackPattern.VACUITY, Language.DAFNY),
    (CryptoPrimitive.ML_KEM_768, AttackPattern.DOMAIN_RESTRICTION, Language.DAFNY),
    (CryptoPrimitive.ML_DSA_65, AttackPattern.PREDICATE_SWAP, Language.DAFNY),
    (CryptoPrimitive.CHACHA20_POLY1305, AttackPattern.IMPLEMENTATION_LEAK, Language.DAFNY),
    (CryptoPrimitive.ML_KEM_1024, AttackPattern.VACUITY, Language.LEAN),
    (CryptoPrimitive.ML_DSA_87, AttackPattern.IMPLEMENTATION_LEAK, Language.LEAN),
    (CryptoPrimitive.ML_KEM_768, AttackPattern.IMPLEMENTATION_LEAK, Language.LEAN),
    (CryptoPrimitive.ML_KEM_512, AttackPattern.DOMAIN_RESTRICTION, Language.VERUS),
    (CryptoPrimitive.ED25519, AttackPattern.PREDICATE_SWAP, Language.VERUS),
    (CryptoPrimitive.AES_GCM_256, AttackPattern.PREDICATE_SWAP, Language.VERUS),
]


def build_sanity_jobs() -> list[tuple]:
    """Multi-language 10-triple sanity batch: 4 Dafny + 3 Lean + 3 Verus.

    Each job is seeded from a distinct registered crypto anchor (see
    ``_SANITY_KEYS``), so the new Lean and Verus anchors are exercised
    directly. All four attack patterns appear, with two vacuity jobs on
    different languages. The four Fireworks families are round-robined across
    the 10 jobs, so every model is exercised at least twice.
    """
    fam_cycle = itertools.cycle(ELICITOR_FAMILIES)
    jobs: list[tuple] = []
    for prim, attack, lang in _SANITY_KEYS:
        a = get_anchor(prim, attack, lang)
        if a is None:  # pragma: no cover - guarded by the registry tests
            raise RuntimeError(f"sanity anchor missing: {prim} {attack} {lang}")
        prob = SourceProblem(
            nl=a.nl_requirement,
            spec=a.original_spec,
            language=lang,
            difficulty=Difficulty.HARD,
            source=SourceBenchmark.LIBCRUX_BUG,
            crypto=a.primitive,
        )
        jobs.append((prob, attack, next(fam_cycle)))
    return jobs


async def run(jobs: list[tuple], concurrency: int, temperature: float) -> dict:
    out_root = Path("data/triples")
    out_root.mkdir(parents=True, exist_ok=True)
    if not jobs:
        log.warning("No jobs - nothing to generate.")
        return {}

    sem = asyncio.Semaphore(concurrency)
    stats: dict[str, dict] = {f: {"ok": 0, "fail": 0, "secs": 0.0} for f in ELICITOR_FAMILIES}
    ok = 0

    async def bounded(problem, attack, family):
        nonlocal ok
        async with sem:
            t0 = time.time()
            try:
                # Reasoning models spend many tokens "thinking"; give each
                # family enough headroom to also emit the full JSON answer.
                max_tokens = FAMILY_MAX_TOKENS.get(family, DEFAULT_MAX_TOKENS)
                client = get_client(
                    family, temperature=temperature, max_tokens=max_tokens
                )
                triple: Triple = await elicit_triple(
                    client=client,
                    problem=problem,
                    attack_pattern=attack,
                    temperature=temperature,
                )
            except Exception as exc:  # noqa: BLE001 - log and continue the batch
                stats[family]["fail"] += 1
                log.warning("gen failed (%s/%s): %s", attack.value, family, exc)
                return
            dt = time.time() - t0
            stats[family]["ok"] += 1
            stats[family]["secs"] += dt
            d = out_root / triple.language.value / triple.difficulty.value
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{triple.triple_id}.json").write_text(triple.model_dump_json(indent=2))
            ok += 1

    tasks = [asyncio.create_task(bounded(p, a, f)) for p, a, f in jobs]
    for fut in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="eliciting"):
        await fut

    log.info("Generated %d / %d triples into %s", ok, len(jobs), out_root)
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-cell", type=int, default=125,
                    help="triples per (language, attack) cell; 125 -> 1500 total")
    ap.add_argument("--concurrency", type=int, default=CONCURRENCY)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--sanity", action="store_true",
                    help="generate the 10-triple sanity batch and stop")
    args = ap.parse_args()

    if args.sanity:
        jobs = build_sanity_jobs()
    elif args.per_cell == 125:
        jobs = build_jobs(CELL_SPLIT)
    else:
        # Scale the 33/67/25 split proportionally for smaller runs.
        scale = args.per_cell / 125
        split = {d: max(1, round(n * scale)) for d, n in CELL_SPLIT.items()}
        jobs = build_jobs(split)

    stats = asyncio.run(run(jobs, args.concurrency, args.temperature))

    print("\nPer-model results:")
    for fam, s in stats.items():
        done = s["ok"]
        avg = (s["secs"] / done) if done else 0.0
        print(f"  {fam:20s} ok={s['ok']:4d} fail={s['fail']:3d} avg={avg:5.1f}s/triple")


if __name__ == "__main__":
    main()
