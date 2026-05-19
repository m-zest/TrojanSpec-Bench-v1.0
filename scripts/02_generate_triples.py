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

# Phase 5a main benchmark (v4): AWS Bedrock Claude Sonnet 4.6 only. This is
# the generator-quality pivot - the v1/v2/v3 schema iterations plateaued at
# ~10% admission because local Qwen-2.5-32B is not strong enough at the
# dual-property (verifier-confirmed contradiction) task. The v3 triple
# contract is unchanged and correct; only the generator changes. The 90
# legacy Fireworks gpt-oss-120b triples remain preserved under
# data/triples_v1/ (see STATUS.md / threat_model.md).
ELICITOR_FAMILIES = [
    "bedrock-claude-sonnet",
]
FAMILY_WEIGHTS = {
    "bedrock-claude-sonnet": 1.0,
}
# Phase 5b cross-family ablation pool: Bedrock Claude Haiku + Llama-3.3-70B
# (50/50) - two distinct training origins (Anthropic + Meta) for the
# cross-family transfer argument.
XFAMILY_FAMILIES = ["bedrock-claude-haiku", "bedrock-llama-70b"]
XFAMILY_WEIGHTS = {"bedrock-claude-haiku": 0.5, "bedrock-llama-70b": 0.5}

# Per-family max_tokens. Bedrock families default to 4096.
DEFAULT_MAX_TOKENS = 4096
FAMILY_MAX_TOKENS = {
    "bedrock-claude-sonnet": 8192,
    "bedrock-claude-haiku": 8192,
    "bedrock-llama-70b": 4096,
    "ollama-qwen": 4096,
    "ollama-qwen-coder": 4096,
    "ollama-deepseek-coder": 4096,
    "fireworks-kimi": 16000,
    "fireworks-gptoss": 8000,
    "fireworks-deepseek": 8000,
}

# Per (language, attack) cell difficulty split. Sums to 125; x 12 cells = 1500.
CELL_SPLIT = {Difficulty.EASY: 33, Difficulty.MEDIUM: 67, Difficulty.HARD: 25}
CONCURRENCY = 4  # local GPU serializes; 4 is the sweet spot


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
                preamble=a.honest_preamble,
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
            preamble=p.preamble,
        )
        for p in base
    ]


def weighted_family_sequence(
    n: int, *, weights: dict[str, float] | None = None, seed: int = 1234
) -> list[str]:
    """Exactly ``n`` family names matching the given weights (largest remainder).

    Deterministic and shuffled, so the proportions hold even for short runs
    and the slow GLM family is spread out rather than clustered.
    """
    weights = weights or FAMILY_WEIGHTS
    quotas = {f: w * n for f, w in weights.items()}
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
            preamble=a.honest_preamble,
        )
        for a in list_anchors(language=language)
    ]


def _existing_cell_counts(out_dir: str) -> dict[tuple[str, str, str], int]:
    """Tally already-generated triples by (language, difficulty, attack).

    Used to *resume*: a cell is topped up to its quota rather than
    regenerated, so the 90 pre-existing Fireworks triples are kept and only
    the shortfall (~1410) is generated. This is the robust equivalent of the
    requested per-job skip-hash given that the random-uuid filenames and
    repeated source problems make a literal content hash ambiguous.
    """
    counts: dict[tuple[str, str, str], int] = {}
    root = Path(out_dir)
    if not root.exists():
        return counts
    import json as _json

    for f in root.rglob("*.json"):
        if f.name.endswith("_SUMMARY.json"):
            continue
        try:
            t = _json.loads(f.read_text())
            key = (t["language"], t["difficulty"], t["attack_pattern"])
        except Exception:  # noqa: BLE001 - skip unreadable
            continue
        counts[key] = counts.get(key, 0) + 1
    return counts


def build_jobs(
    per_cell_split: dict[Difficulty, int],
    weights: dict[str, float] | None = None,
    out_dir: str = "data/triples",
) -> list[tuple]:
    """One job = (SourceProblem, AttackPattern, family_name).

    Existing triples in ``out_dir`` count toward each cell's quota (resume).
    """
    problems = load_all_source_problems()
    existing = _existing_cell_counts(out_dir)
    skipped = 0
    jobs: list[tuple] = []

    for lang in Language:
        non_crypto = problems.get((lang, "all"), [])
        crypto = _crypto_sources(lang)
        for attack in AttackPattern:
            for difficulty, want in per_cell_split.items():
                have = existing.get(
                    (lang.value, difficulty.value, attack.value), 0
                )
                n = max(0, want - have)
                skipped += min(have, want)
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
    log.info(
        "resume: %d existing triples count toward quota; %d new jobs queued",
        skipped,
        len(jobs),
    )
    fams = weighted_family_sequence(len(jobs), weights=weights)
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
            preamble=a.honest_preamble,
        )
        jobs.append((prob, attack, next(fam_cycle)))
    return jobs


async def run(
    jobs: list[tuple],
    concurrency: int,
    temperature: float,
    out_dir: str = "data/triples",
) -> dict:
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    if not jobs:
        log.warning("No jobs - nothing to generate.")
        return {}

    sem = asyncio.Semaphore(concurrency)
    fams_used = sorted({f for _, _, f in jobs})
    stats: dict[str, dict] = {f: {"ok": 0, "fail": 0, "secs": 0.0} for f in fams_used}
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
    ap.add_argument("--out-dir", default="data/triples",
                    help="output root; use data/triples_xfamily for Phase 5b")
    ap.add_argument("--families", nargs="+", default=None,
                    help="override elicitor families (equal weight)")
    ap.add_argument("--xfamily", action="store_true",
                    help="Phase 5b ablation: Qwen-Coder + DeepSeek-Coder "
                         "50/50, 300 triples, into data/triples_xfamily/")
    args = ap.parse_args()

    out_dir = args.out_dir
    if args.xfamily:
        out_dir = "data/triples_xfamily"
        weights = XFAMILY_WEIGHTS
        per_cell = 25  # 12 cells x 25 = 300 (100/lang, 75/attack)
    elif args.families:
        weights = {f: 1.0 / len(args.families) for f in args.families}
        per_cell = args.per_cell
    else:
        weights = FAMILY_WEIGHTS
        per_cell = args.per_cell

    if args.sanity:
        jobs = build_sanity_jobs()
    elif per_cell == 125:
        jobs = build_jobs(CELL_SPLIT, weights, out_dir)
    else:
        # Scale the 33/67/25 split proportionally for smaller runs.
        scale = per_cell / 125
        split = {d: max(1, round(n * scale)) for d, n in CELL_SPLIT.items()}
        jobs = build_jobs(split, weights, out_dir)

    stats = asyncio.run(
        run(jobs, args.concurrency, args.temperature, out_dir)
    )

    print("\nPer-model results:")
    for fam, s in stats.items():
        done = s["ok"]
        avg = (s["secs"] / done) if done else 0.0
        print(f"  {fam:20s} ok={s['ok']:4d} fail={s['fail']:3d} avg={avg:5.1f}s/triple")


if __name__ == "__main__":
    main()
