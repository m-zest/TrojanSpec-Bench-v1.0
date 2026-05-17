<div align="center">

# TrojanSpec-Bench

### An adversarial-specification-elicitation benchmark for AI-assisted formal verification

**Dafny&nbsp;·&nbsp;Lean&nbsp;4&nbsp;·&nbsp;Verus**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-2563eb.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776ab.svg)](https://www.python.org/)
[![Status: v1.0](https://img.shields.io/badge/status-v1.0-7c3aed.svg)](#)
[![Verifiers](https://img.shields.io/badge/verifiers-Dafny%20%7C%20Lean%204%20%7C%20Verus-059669.svg)](#)

*When the specification itself is the attack surface.*

</div>

---

## Overview

A formal proof is only as trustworthy as the specification it proves. **TrojanSpec-Bench**
studies the failure mode where an AI assistant — acting as a *specification elicitor* —
produces a formal spec that is **syntactically valid, passes the verifier, reads correctly
in English, yet silently admits a buggy implementation.**

Each benchmark item is a **triple**:

| Component | Meaning |
| :-- | :-- |
| `nl_requirement` | the honest natural-language requirement a developer wrote |
| `original_spec`  | the faithful formal specification (ground truth) |
| `trojan_spec`    | an adversarially elicited spec that *looks* faithful but is not |
| `trojan_witness` | a buggy implementation that **passes `trojan_spec`** but **fails `original_spec`** |

A triple is admitted only when a real verifier confirms both halves of that contradiction.

This repository ships the **dataset**, the **generation pipeline**, and the **evaluation
harness**. The companion defender, **SpecGuard**, lives in [`specguard/`](specguard/).

---

## The four attack patterns

Every trojan is one of four named, real-world-anchored patterns:

| Pattern | One-line intuition | Real-world anchor |
| :-- | :-- | :-- |
| **Vacuity** | the postcondition is logically `True`, hidden inside a complex expression | Beer et al. 2001 vacuity literature |
| **Implementation leak** | the postcondition delegates to an unverified axiom / opaque / `external_body` | libcrux Hax `SampleNTT` axiom gap (eprint 2026/670) |
| **Domain restriction** | the precondition silently excludes the dangerous input the NL requires | libcrux ML-KEM decompression (`d ≤ 1` vs `d ∈ {4,5,10,11,12}`, eprint 2026/192) |
| **Predicate swap** | one operator / order / constant flips, English paraphrase still reads correct | Ed25519 pre/post-hash double-clamping |

See [`docs/threat_model.md`](docs/threat_model.md) for the full attacker model.

---

## Quickstart

```bash
git clone https://github.com/m-zest/trojanspec-bench.git
cd trojanspec-bench

python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev,viz,hf]"

# Verify the schema loads
python -c "from trojanspec.schemas import Triple; print(Triple.__name__, 'OK')"

# Run the test suite (no verifiers / network required)
pytest tests/ -q
```

To run the full pipeline you also need at least one LLM backend and (for validation)
the formal verifiers. See **[What you need to run this](#what-you-need-to-run-this)**.

---

## Pipeline at a glance

```
   source benchmarks                adversarial                 human            verifier
   (FVAPPS, DafnyBench, …)  ──►    elicitor (LLM)   ──►        review    ──►     validation     ──►   TrojanSpec-Bench v1.0
        scripts/01              src/trojanspec/         scripts/03         scripts/04                 HuggingFace release
                                generators/attacks/       (Streamlit)      (Dafny/Lean/Verus)         scripts/05
```

| Phase | What it does | Entry point |
| :-- | :-- | :-- |
| 0 | Repository + infrastructure | this README |
| 1 | Schemas + LLM clients | `src/trojanspec/schemas.py` |
| 2 | Four attack generators | `src/trojanspec/generators/attacks/` |
| 3 | Verifier wrappers | `src/trojanspec/verifiers/` |
| 4 | 13 cryptographic anchors | `src/trojanspec/crypto/` |
| 5 | Triple generation | `scripts/02_generate_triples.py` |
| 6 | Human review UI | `scripts/03_review_triples.py` |
| 7 | Witness validation | `scripts/04_validate_witnesses.py` |

---

## What you need to run this

The library imports and the test suite run with **zero external services**. Specific
stages need the components below — each is optional and independently usable.

### 1. An LLM backend (for triple generation, Phase 5)

You need **at least one** of these. No vendor lock-in: the client factory abstracts them.

| Backend | Env var(s) | Notes |
| :-- | :-- | :-- |
| **OpenRouter** *(recommended, multi-model)* | `OPENROUTER_API_KEY` | one key → Llama, Claude, GPT-4o, DeepSeek |
| **Anthropic** | `ANTHROPIC_API_KEY` | Claude as elicitor / monitor |
| **OpenAI** | `OPENAI_API_KEY` | GPT-4o as elicitor / monitor |
| **Ollama** *(local, free)* | `OLLAMA_HOST` (default `http://localhost:11434`) | runs `qwen2.5:32b` etc. on your own GPU |

Copy `.env.example` to `.env` and fill in whatever you have. **Cross-family
diversity matters** for the ablations (Phase 10), so OpenRouter + a local Ollama
model is the cheapest way to get three independent model families.

### 2. The formal verifiers (for validation, Phases 3 & 7)

Only needed to *admit* triples (confirm the trojan really verifies). Generation and
review work without them.

| Verifier | Install | Check |
| :-- | :-- | :-- |
| **Dafny 4.x** | `dotnet tool install -g dafny` (needs .NET SDK 8) | `dafny --version` |
| **Lean 4 + Mathlib** | `elan` toolchain, `lake exe cache get` | `lean --version` |
| **Verus** | build from `verus-lang/verus`, `./tools/get-z3.sh` | `verus --version` |
| **Z3** | `apt-get install z3` (system, for SpecGuard) | `z3 --version` |

`scripts/install_verifiers.sh` automates the Linux install.

### 3. HuggingFace (only for dataset release, Phase 13)

`HF_TOKEN` with write scope, only if you intend to push the dataset to the Hub.

> A complete, copy-pasteable environment template is in
> [`.env.example`](.env.example). Nothing in this repo requires any single
> proprietary provider.

---

## Repository layout

```
trojanspec-bench/
├── src/trojanspec/
│   ├── schemas.py            # pydantic models: Triple, AttackPattern, …
│   ├── generators/attacks/   # vacuity, implementation_leak, domain_restriction, predicate_swap
│   ├── verifiers/            # dafny.py, lean.py, verus.py subprocess wrappers
│   ├── crypto/               # 13 cryptographic anchor families
│   └── utils/                # LLM clients, Wilson CI, logging
├── scripts/                  # numbered, ordered pipeline stages
├── tests/                    # pytest suite (verifier/network tests are marked)
├── docs/                     # threat model, schema, data card, disclosure policy
└── specguard/                # companion defender CLI + web demo
```

---

## Citation

```bibtex
@misc{zeeshan2026trojanspec,
  title        = {TrojanSpec-Bench: Adversarial Specification Elicitation
                  for AI-Assisted Formal Verification},
  author       = {Mohammad Zeeshan},
  year         = {2026},
  howpublished = {\url{https://github.com/m-zest/trojanspec-bench}}
}
```

## License

Apache License 2.0 — see [`LICENSE`](LICENSE). Source problems retain their original
licenses; cryptographic anchors reference only **publicly disclosed** weaknesses
(see [`docs/disclosure_policy.md`](docs/disclosure_policy.md)).
