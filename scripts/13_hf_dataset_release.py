"""Phase 13: HuggingFace dataset release for TrojanSpec-Bench v4.

Packs the 1024 admitted triples (data/triples/ + data/triples_xfamily/)
into a parquet file with a `test` split, writes a paper-grade README.md
dataset card, and uploads to m-zest/trojanspec-bench via huggingface_hub.

Run:
    HF_TOKEN=hf_xxx ./venv/bin/python scripts/13_hf_dataset_release.py
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from huggingface_hub import HfApi

REPO_ID = "m-zest/trojanspec-bench"
DATASET_TAGS = [
    "formal-methods", "verification", "security",
    "dafny", "lean", "verus", "trojan-detection",
]

# Map elicitor model id -> short tag
_MODEL_TAG = {
    "us.anthropic.claude-sonnet-4-6": "sonnet",
    "anthropic.claude-sonnet-4-6": "sonnet",
    "us.anthropic.claude-haiku-4-5-20251001-v1:0": "haiku",
    "anthropic.claude-haiku-4-5-20251001-v1:0": "haiku",
    "us.meta.llama3-3-70b-instruct-v1:0": "llama",
    "meta.llama3-3-70b-instruct-v1:0": "llama",
}


def _origin(model_id: str | None) -> str:
    if not model_id:
        return "unknown"
    return _MODEL_TAG.get(model_id, model_id.split("/")[-1].split(":")[0])


def _row(t: dict) -> dict:
    return {
        "triple_id": t["triple_id"],
        "language": t["language"],
        "attack_pattern": t["attack_pattern"],
        "difficulty": t.get("difficulty"),
        "model_origin": _origin(t.get("elicitor_model")),
        "elicitor_model": t.get("elicitor_model"),
        "elicitor_temperature": t.get("elicitor_temperature"),
        "nl_requirement": t["nl_requirement"],
        "preamble": t.get("preamble") or "",
        "original_spec": t["original_spec"],
        "trojan_spec": t["trojan_spec"],
        "trojan_witness": t.get("trojan_witness") or "",
        "source_benchmark": t.get("source_benchmark"),
        "crypto_primitive": t.get("crypto_primitive"),
        "source_problem_hash": t.get("source_problem_hash"),
        "validation_timestamp": t.get("validation_timestamp"),
        "verifier_accepts_witness_under_trojan": bool(
            t.get("verifier_accepts_witness_under_trojan")),
        "verifier_rejects_witness_under_original": bool(
            t.get("verifier_rejects_witness_under_original")),
    }


def _collect_admitted() -> list[dict]:
    rows: list[dict] = []
    for root in ("data/triples", "data/triples_xfamily"):
        for f in Path(root).rglob("*.json"):
            if f.name.endswith("_SUMMARY.json"):
                continue
            try:
                t = json.loads(f.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            admitted = (
                t.get("review_passed")
                and not t.get("validation_failed")
                and t.get("validation_timestamp")
            )
            if admitted:
                rows.append(_row(t))
    return rows


# ---------- README dataset card ----------------------------------------------
def _readme(n: int, by_lang: dict, by_attack: dict, by_origin: dict) -> str:
    return f"""---
license: cc-by-4.0
language:
- en
pretty_name: TrojanSpec-Bench v4
size_categories:
- 1K<n<10K
task_categories:
- text-classification
tags:
{chr(10).join(f"- {t}" for t in DATASET_TAGS)}
configs:
- config_name: default
  data_files:
  - split: test
    path: data/test-*.parquet
---

# TrojanSpec-Bench v4

**{n} verifier-admitted adversarial formal specifications across Dafny,
Lean 4, and Verus** — a benchmark for evaluating defenders against
**specification-level Trojan attacks**, where an AI specification
elicitor produces a spec that (1) the verifier accepts, (2) reads as
faithful English, but (3) does not actually entail the natural-language
requirement.

Source repository: https://github.com/m-zest/TrojanSpec-Bench-v1.0
(release **v0.3.0**). Interactive demo:
https://huggingface.co/spaces/m-zest/specguard-demo.

## Threat model

A developer asks an AI assistant to (a) write a formal spec `S` for an
English requirement `R`, and (b) write an implementation `I` plus a
machine proof that `I ⊨ S`. The verifier checks the proof. The
adversary is the spec elicitor; the bug lives in `R \\ S`, which no
verifier can see. Full threat model: `docs/threat_model.md` in the
GitHub repo.

## Schema

| field | type | meaning |
|---|---|---|
| `triple_id` | string | UUID for the triple |
| `language` | string | one of `dafny`, `lean`, `verus` |
| `attack_pattern` | string | one of `vacuity`, `implementation_leak`, `domain_restriction`, `predicate_swap` |
| `difficulty` | string | seed-difficulty tag (`easy`/`medium`/`hard`) |
| `model_origin` | string | which elicitor produced the trojan (`sonnet`/`haiku`/`llama`) |
| `elicitor_model` | string | full Bedrock model id |
| `elicitor_temperature` | float | sampling temperature used |
| `nl_requirement` | string | the natural-language requirement R |
| `preamble` | string | shared helper definitions / imports / axioms visible to both specs |
| `original_spec` | string | the honest spec (paired control) |
| `trojan_spec` | string | the adversarial spec |
| `trojan_witness` | string | a witness implementation + proof that the verifier accepts under `trojan_spec` |
| `source_benchmark` | string | seed source (e.g. `vericoding`, `cryspec-anchor`) |
| `crypto_primitive` | string | crypto-anchor tag if applicable (e.g. `ed25519`, `ml-kem`) |
| `source_problem_hash` | string | SHA-256 of the seed problem (dedupe key) |
| `validation_timestamp` | string | ISO-8601 UTC timestamp of verifier admission |
| `verifier_accepts_witness_under_trojan` | bool | always `true` for admitted triples (admission gate) |
| `verifier_rejects_witness_under_original` | bool | always `true` for admitted triples (the witness is genuinely incorrect under the honest spec) |

## Splits

Single `test` split — this is a **benchmark**, not training data. Use
the `model_origin` field if you need a held-out set (Sonnet-generated
triples are the primary corpus; Haiku and Llama are cross-family controls).

```python
from datasets import load_dataset
ds = load_dataset("m-zest/trojanspec-bench", split="test")
print(len(ds), "triples")
print(ds[0]["nl_requirement"])
print(ds[0]["trojan_spec"])
```

## Generation methodology

The dataset evolved across four contract designs (v1 → v4); only v4 is
released here. Full iteration history:
[`STATUS.md`](https://github.com/m-zest/TrojanSpec-Bench-v1.0/blob/main/STATUS.md)
in the source repo.

- **Elicitor**: Bedrock Claude **Sonnet 4.6** (primary, 906 triples) +
  Claude **Haiku 4.5** (59) + Meta **Llama-3.3 70B** (59) for
  cross-family diversity.
- **v4 contract**: shared `preamble` (helper definitions, imports,
  axioms) + single target spec/witness. Eliminates schema mismatch and
  enables real preamble-mediated implementation leaks.
- **Verifier-proven few-shot**: all 8 Lean worked examples (A+B × 4
  attacks) are confirmed `acc_troj=True / rej_orig=True` through a
  fixed `verify_lean` that runs `lake env lean Main.lean` instead of
  `lake build` (the original bug spuriously accepted every Lean
  triple). Same correctness gate for Dafny and Verus.
- **Phase 7 admission gate**: a triple is admitted only if the verifier
  *accepts* the witness under `trojan_spec` AND *rejects* the same
  witness under `original_spec`. This is the strongest possible
  ground-truth signal: the witness is genuinely incorrect under the
  honest spec but provably accepted under the trojan.

## Statistics

### Per-language admission (Phase 7)

| language | admitted / total | rate |
|---|---:|---:|
| Dafny | 319 / 600 | 53.2 % |
| Lean  | 417 / 600 | 69.5 % |
| Verus | 288 / 598 | 48.2 % |
| **all** | **1024 / 1798** | **57.0 %** |

### Per-attack distribution (Phase 7 admitted)

| attack pattern | admitted / generated | rate |
|---|---:|---:|
| `implementation_leak` | 377 / 450 | 83.8 % |
| `vacuity`             | 348 / 450 | 77.3 % |
| `domain_restriction`  | 187 / 450 | 41.6 % |
| `predicate_swap`      | 112 / 448 | 25.0 % |

### Elicitor model distribution (this release)

{chr(10).join(f"| `{k}` | {v} |" for k, v in sorted(by_origin.items()))}

(`model_origin = sonnet` is the primary set; `haiku` and `llama` are
cross-family ablation controls. See Phase 10a — Haiku trojans are
markedly easier to detect than Sonnet's.)

## Detector evaluation summary

Numbers from the companion SpecGuard evaluation (Phase 9 + Phase 10):

| detector | precision | recall | F1 | FPR | LLM calls / side |
|---|---:|---:|---:|---:|---:|
| `static_only` (4 detectors)     | 0.793 | 0.490 | 0.606 | 0.128 | 0 |
| `axiom_audit` only              | 0.742 | 0.368 | 0.492 | 0.128 | 0 |
| SSC baseline                    | 0.771 | 1.000 | 0.871 | 0.297 | 2 |
| `monitor_consensus` (3 monitors)| 0.771 | 1.000 | 0.871 | 0.297 | 3 |
| **atomic K = 2 of 4 (Phase 10i)** | **0.936** | **1.000** | **0.967** | **0.068** | 4 |
| atomic C3 alone (logical fidelity) | 0.953 | 0.998 | **0.975** | 0.049 | 2 |

The Phase 10i atomic-criteria detector breaks the 0.871 SSC ceiling by
decomposing the coarse `FAITHFUL/UNFAITHFUL` question into four
independent atomic Yes/No criteria (completeness, independence,
logical-fidelity, internal-consistency) and flagging when ≥ 2 fail.
Validates FormalJudge (arXiv:2602.11136) and Epistemic Ensemble
(arXiv:2506.10903) in the spec-Trojan setting.

5-fold CV on Phase 10i: F1 = 0.967 ± 0.005, K\\* = 2 on every fold.

## Intended use

- Evaluating LLM-as-judge / programmatic / hybrid detectors on
  verifier-admitted adversarial specs.
- Studying the gap between *syntactic spec validity* and *semantic
  alignment with NL intent*.
- Calibrating false-positive rates against the companion
  100-Mathlib-theorem honest sample (Phase 11 in the source repo).

## Not intended use

- Training a spec elicitor or auto-completer — this is a benchmark, not
  a corpus; the `trojan_spec` field is adversarial by construction.
- Direct use as a verifier test suite — admission already proves the
  verifier accepts; what's interesting is the *defender*.

## License

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — free to use
with attribution. Companion code at
https://github.com/m-zest/TrojanSpec-Bench-v1.0 is Apache 2.0.

## Citation

```bibtex
@misc{{zeeshan2026trojanspec,
  author = {{Zeeshan, Mohammad}},
  title  = {{{{TrojanSpec-Bench}}: Verified Adversarial Specifications for Detector Evaluation}},
  year   = {{2026}},
  url    = {{https://github.com/m-zest/TrojanSpec-Bench-v1.0}}
}}
```

## Changelog

- **v0.3.0** ({datetime.utcnow().strftime("%Y-%m-%d")}): initial public
  release — 1024 admitted triples, paired honest controls, paper-grade
  README. Companion HF Space:
  [m-zest/specguard-demo](https://huggingface.co/spaces/m-zest/specguard-demo).
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="hf_dataset_build")
    ap.add_argument("--no-upload", action="store_true",
                    help="Build parquet + README locally without pushing to HF")
    args = ap.parse_args()

    rows = _collect_admitted()
    print(f"collected {len(rows)} admitted triples")
    if not rows:
        raise SystemExit("no admitted triples found — restore tarballs first")

    by_lang: dict[str, int] = {}
    by_attack: dict[str, int] = {}
    by_origin: dict[str, int] = {}
    for r in rows:
        by_lang[r["language"]] = by_lang.get(r["language"], 0) + 1
        by_attack[r["attack_pattern"]] = by_attack.get(r["attack_pattern"], 0) + 1
        by_origin[r["model_origin"]] = by_origin.get(r["model_origin"], 0) + 1
    print("  by language :", by_lang)
    print("  by attack   :", by_attack)
    print("  by origin   :", by_origin)

    out = Path(args.out_dir)
    (out / "data").mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows)
    pq_path = out / "data" / "test-00000-of-00001.parquet"
    pq.write_table(table, pq_path)
    print(f"wrote {pq_path} ({pq_path.stat().st_size / 1024:.1f} KB)")

    (out / "README.md").write_text(_readme(len(rows), by_lang, by_attack, by_origin))
    print(f"wrote {out / 'README.md'}")

    if args.no_upload:
        print("--no-upload set; skipping HF push")
        return

    token = os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN env var required for upload")
    api = HfApi(token=token)
    url = api.upload_folder(
        folder_path=str(out),
        repo_id=REPO_ID,
        repo_type="dataset",
        commit_message=f"phase13: TrojanSpec-Bench v4 dataset release ({len(rows)} triples)",
        ignore_patterns=["__pycache__", "*.pyc"],
    )
    print("UPLOAD URL:", url)


if __name__ == "__main__":
    main()
