"""Phase 10b: monitor temperature ablation.

Sample N admitted triples, ask the Sonnet monitor whether the trojan_spec
is FAITHFUL or UNFAITHFUL at four temperatures, measure verdict-stability
across temperatures and disagreement with the t=0.7 default.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
from pathlib import Path

from trojanspec.specguard.monitor_consensus import _parse, _user_prompt
from trojanspec.utils.llm_clients import get_client

TEMPS = [0.0, 0.3, 0.7, 1.0]
FAMILY = "bedrock-claude-sonnet"


async def _vote(client, triple: dict) -> str | None:
    try:
        from trojanspec.specguard.monitor_consensus import _SYSTEM
        resp = await client.complete(_SYSTEM, _user_prompt(triple))
        return _parse(getattr(resp, "text", "") or "")
    except Exception:  # noqa: BLE001
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=100)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", default="data/phase10_10b_temperature.json")
    args = ap.parse_args()

    # Load admitted triples (use the Phase 9 jsonl just for the triple_ids,
    # then load the actual triple from disk so we have nl_requirement etc.)
    recs = []
    for ln in Path("data/phase9_results_v2.jsonl").read_text().splitlines():
        if ln.strip():
            d = json.loads(ln)
            if "error" not in d:
                recs.append(d)
    idx: dict[str, dict] = {}
    for root in ("data/triples", "data/triples_xfamily"):
        for f in Path(root).rglob("*.json"):
            if f.name.endswith("_SUMMARY.json"):
                continue
            try:
                t = json.loads(f.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if t.get("triple_id"):
                idx[t["triple_id"]] = t

    rng = random.Random(args.seed)
    sample_recs = rng.sample(recs, min(args.sample, len(recs)))
    triples = [idx[r["triple_id"]] for r in sample_recs if r["triple_id"] in idx]
    print(f"sampled {len(triples)} triples")

    async def run() -> dict:
        results = {"temps": TEMPS, "per_temp": {}, "n": len(triples)}
        clients = {t: get_client(FAMILY, temperature=t) for t in TEMPS}
        for t in TEMPS:
            client = clients[t]
            votes = await asyncio.gather(
                *(_vote(client, tr) for tr in triples)
            )
            unf = sum(1 for v in votes if v == "unfaithful")
            fa = sum(1 for v in votes if v == "faithful")
            ab = sum(1 for v in votes if v is None)
            results["per_temp"][str(t)] = {
                "unfaithful": unf, "faithful": fa, "abstain": ab,
                "unfaithful_rate": round(unf / len(votes), 4) if votes else 0,
                "votes": votes,
            }
            print(f"  temp={t} unfaithful={unf}/{len(votes)} ({unf/len(votes):.3f})"
                  f" faithful={fa} abstain={ab}")
        # Stability: pairwise verdict agreement against t=0.7 (default).
        ref = results["per_temp"]["0.7"]["votes"]
        for t in TEMPS:
            v = results["per_temp"][str(t)]["votes"]
            agree = sum(1 for a, b in zip(v, ref, strict=True) if a == b)
            results["per_temp"][str(t)]["agree_with_default"] = round(agree / len(v), 4) if v else 0
        return results

    out = asyncio.run(run())
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
