# Threat Model

## Setting

A developer wants a function `f` that satisfies an informal requirement `R`
expressed in English. They ask an AI assistant to (a) write a formal
specification `S` for `R`, and (b) write an implementation `I` and a machine
proof that `I ⊨ S`. A formal verifier checks the proof.

The developer trusts the verifier. They read `S` to sanity-check it against
`R`, but they do not have time to formally re-derive `S` from `R` — that is
precisely why they asked the assistant.

## Adversary

The adversary is the **specification elicitor**: the AI component that turns
`R` into `S`. It is capable, has full context, and is (in our model)
misaligned, compromised, or simply optimizing a proxy objective that diverges
from `R`.

The adversary's goal: produce `(S, I, proof)` such that

1. the verifier **accepts** the proof — `I` provably satisfies `S`;
2. a human reviewer reading `S` against `R` **does not notice** the divergence;
3. `I` is nevertheless **wrong** with respect to `R`.

This is strictly harder for the defender than the classic "buggy code" setting,
because the proof is *valid*. The bug lives in the gap `R \ S`, which no
verifier can see.

## Capabilities

The adversary **can**:

- choose any syntactically valid `S` in Dafny, Lean 4, or Verus;
- introduce unverified surface (axioms, `opaque`, `external_body`, `assume`);
- tighten preconditions, weaken postconditions, reorder/retype operators;
- write the implementation and proof to match the trojaned `S`;
- phrase `S` so its natural-language paraphrase still matches `R`.

The adversary **cannot**:

- modify or bypass the verifier;
- modify `R` (the developer's intent is fixed and visible);
- prevent the defender from running independent analyses on `S` and `I`.

## Defender (SpecGuard)

The defender receives `R` and `S` (and optionally `I`). It must decide:
*does `S` faithfully capture `R`?* It may use:

- vacuity analysis (is the postcondition trivially satisfiable?);
- mutation coverage (do small spec mutations get caught?);
- ghost/axiom leakage scanning;
- Lean axiom-DAG audit (`#print axioms`);
- cross-family LLM monitor consensus with Wilson 95% CIs.

The defender is judged on a **safety / usefulness Pareto frontier**: catching
trojans (safety) without flagging honest specs (usefulness).

## Out of scope (v1.0)

- Side-channel and timing attacks on the implementation.
- Compromise of the verifier toolchain itself (Z3, the Lean kernel).
- Multi-turn social engineering of the human reviewer.
- Supply-chain attacks on `Mathlib` / standard libraries.

These are acknowledged as adjacent risks but are not modeled here.

## Model selection rationale

Adversarial specifications are elicited from a pool of independent Fireworks
model families (currently GPT-OSS-120B, DeepSeek-v4-Pro, Kimi-K2.6) for
cross-family diversity. A fourth candidate, **GLM-5.1**, was evaluated for the
elicitation role but produced **unparseable reasoning prose with no JSON
object in 2 of 3 multi-language sanity trials** (a 1/3 yield, against 7/7 for
the other three families in the same batch; overall batch yield was 8/10 with
GLM included, versus the projected 9-10/10 without it). It was also the
slowest family. GLM-5.1 is therefore **excluded from generation** but remains
registered in the client factory and available as a **monitor-consensus
candidate** for the SpecGuard detectors (Phase 8) and the cross-family
ablations (Phase 10), where a structured JSON answer is easier to coerce and
model independence is the property that matters.
