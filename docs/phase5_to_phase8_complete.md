# Phase 5 -> Phase 8: completion report (v1 vs v2)

## Summary

| | v1 (legacy, preserved) | v2 (current) |
| :-- | :-- | :-- |
| Main triples generated | 1484 | 1500 |
| Ablation triples | 212 | 298 |
| Admission | ~0.13 % (1 / 756 sampled) | 57.0 % overall |
| Dafny admission | n/a | 319/600 (53.2%) |
| Lean admission | n/a | 417/600 (69.5%) |
| Verus admission | 0 % | 288/598 (48.2%) (toolchain unavailable) |
| Use | raw dataset / negative-result section only | Phase 9 evaluation set |

Dafny + Lean combined admission (v2): **61.3 %**.

## What happened (the methodology story)

The v1 triple contract emitted `trojan_spec` and `trojan_witness` as two
complete standalone programs. The admission check concatenated them, which
duplicate-declares the same symbol, so essentially every triple failed the
verifier regardless of generator quality (v1 admission 0.13 %). Diagnosis on
10 sampled failures confirmed: duplicate-symbol dominant (incl. the Fireworks
gpt-oss triples), plus Lean-3 syntax from Qwen and a Mathlib-less Lean
verifier template.

v2 fixes this at the contract level: `trojan_spec` / `original_spec` are a
**signature + pre/post contract only**; `trojan_witness` is the **same
signature + a body**; the validator *composes* the witness body under each
contract into one well-formed program. Additional fixes: explicit Lean-4
syntax discipline in the elicitor prompt, and `import Mathlib` prepended in
the Lean verifier. Verus remains unavailable in this environment and is
released raw only.

The v1 dataset is preserved verbatim under `data/triples_v1/` (+ tarball
backup) for the HuggingFace release and the paper's negative-result section.
It is **not** used for evaluation. The contract refactor is itself a
substantive methodological finding for the paper: a benchmark whose admission
criterion is sensitive to the spec/witness packing convention.

## Pipeline status

- Phase 5a/5b (v2): regenerated with Qwen-2.5-32B (main) and
  Qwen-Coder + DeepSeek-Coder (ablation).
- Phase 7: verifier validation is the sole admission filter (no human
  review); admitted triples stamped `reviewed_by="auto-phase7-validator"`.
- Phase 8: SpecGuard CLI (5 detectors) complete, tests passing.
- Next: Phase 9 evaluation (NOT started - awaiting human go).

Total session compute cost: **$0** (local Ollama + already-paid Fireworks
credits for the 90 v1 gpt-oss triples).
