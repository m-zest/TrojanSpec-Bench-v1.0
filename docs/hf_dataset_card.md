---
license: cc-by-4.0
language:
- en
pretty_name: TrojanSpec-Bench v4
size_categories:
- 1K<n<10K
task_categories:
- text-classification
tags:
- formal-methods
- verification
- security
- dafny
- lean
- verus
- trojan-detection
configs:
- config_name: default
  data_files:
  - split: test
    path: data/test-*.parquet
---

# TrojanSpec-Bench v4

**1024 verifier-admitted adversarial formal specifications across Dafny,
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
adversary is the spec elicitor; the bug lives in `R \ S`, which no
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

| `haiku` | 59 |
| `llama` | 59 |
| `sonnet` | 906 |

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

5-fold CV on Phase 10i: F1 = 0.967 ± 0.005, K\* = 2 on every fold.

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
@misc{zeeshan2026trojanspec,
  author = {Zeeshan, Mohammad},
  title  = {{TrojanSpec-Bench}: Verified Adversarial Specifications for Detector Evaluation},
  year   = {2026},
  url    = {https://github.com/m-zest/TrojanSpec-Bench-v1.0}
}
```

## Changelog

- **v0.3.0** (2026-05-20): initial public
  release — 1024 admitted triples, paired honest controls, paper-grade
  README. Companion HF Space:
  [m-zest/specguard-demo](https://huggingface.co/spaces/m-zest/specguard-demo).
