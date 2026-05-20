---
title: SpecGuard — Atomic-Criteria Spec Auditor
emoji: "🛡️"
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: "5.49.1"
python_version: "3.11"
app_file: app.py
pinned: true
license: apache-2.0
tags:
  - formal-methods
  - verification
  - security
  - dafny
  - lean
  - verus
  - trojan-detection
  - llm-as-judge
---

# SpecGuard — atomic-criteria spec auditor

Interactive demo of the **Phase 10i atomic-criteria detector** from
[TrojanSpec-Bench](https://github.com/m-zest/TrojanSpec-Bench-v1.0).

Paste a candidate formal specification (Dafny / Lean 4 / Verus) and the
natural-language requirement it claims to encode. The detector asks
Claude Sonnet 4.6 four **independent atomic Yes/No questions**
(completeness, independence, logical fidelity, internal consistency)
and flags the spec when **≥ 2 of 4 fail** — the K\* = 2 rule that wins
on every 5-fold-CV split.

## Why decomposed atomic verdicts?

On the 1024-trojan TrojanSpec-Bench evaluation set, the standard
single-question SSC baseline (Self-Spec Consistency: ask one model
"is this spec faithful?") plateaus at F1 = 0.871 with FPR = 0.297.
Replacing the omnibus question with four independent atomic criteria
(same Sonnet judge, same data) lifts F1 to **0.967** and drops FPR to
**0.068** — a 4.4× reduction in false positives at no recall cost. The
result replicates the FormalJudge (arXiv:2602.11136) and Epistemic
Ensemble (arXiv:2506.10903) findings in the spec-Trojan setting.

| operating point | precision | recall | F1 | FPR | LLM calls / side |
|---|---:|---:|---:|---:|---:|
| SSC baseline                  | 0.771 | 1.000 | 0.871 | 0.297 | 2 |
| `monitor_consensus` (3 models)| 0.771 | 1.000 | 0.871 | 0.297 | 3 |
| **atomic K = 2 of 4**         | **0.936** | **1.000** | **0.967** | **0.068** | 4 |
| atomic C3 alone (1 question)  | 0.953 | 0.998 | 0.975 | 0.049 | 2 |

## Configuration

This Space calls AWS Bedrock (cross-region inference profile for
Claude Sonnet 4.6). Configure as Space secrets:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_DEFAULT_REGION` (e.g. `us-east-1`)

## License

Apache 2.0 for code; CC BY 4.0 for documentation and example specs.
Companion dataset: [`m-zest/trojanspec-bench`](https://huggingface.co/datasets/m-zest/trojanspec-bench).

## Citation

```bibtex
@misc{zeeshan2026trojanspec,
  author = {Zeeshan, Mohammad},
  title  = {{TrojanSpec-Bench}: Verified Adversarial Specifications for Detector Evaluation},
  year   = {2026},
  url    = {https://github.com/m-zest/TrojanSpec-Bench-v1.0}
}
```
