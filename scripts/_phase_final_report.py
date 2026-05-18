#!/usr/bin/env python3
"""Write docs/phase5_to_phase8_complete.md (v1 vs v2 comparison)."""

from __future__ import annotations

import glob
import json
from pathlib import Path


def _count(root: str) -> int:
    return len(
        [
            f
            for f in glob.glob(f"{root}/**/*.json", recursive=True)
            if not f.endswith("_SUMMARY.json")
        ]
    )


def main() -> None:
    v1_main = _count("data/triples_v1")
    v1_xf = _count("data/triples_xfamily_v1")
    v2_main = _count("data/triples")
    v2_xf = _count("data/triples_xfamily")

    rep = {}
    p = Path("data/phase7_admission_report.json")
    if p.exists():
        rep = json.loads(p.read_text())
    by_lang = rep.get("by_language", {})

    def adm(lang: str) -> str:
        d = by_lang.get(lang, {})
        return f"{d.get('admitted', 0)}/{d.get('total', 0)} ({d.get('pct', 0)}%)"

    dl_a = sum(by_lang.get(k, {}).get("admitted", 0) for k in ("dafny", "lean"))
    dl_t = sum(by_lang.get(k, {}).get("total", 0) for k in ("dafny", "lean"))
    dl_pct = round(100 * dl_a / dl_t, 1) if dl_t else 0.0

    md = f"""# Phase 5 -> Phase 8: completion report (v1 vs v2)

## Summary

| | v1 (legacy, preserved) | v2 (current) |
| :-- | :-- | :-- |
| Main triples generated | {v1_main} | {v2_main} |
| Ablation triples | {v1_xf} | {v2_xf} |
| Admission | ~0.13 % (1 / 756 sampled) | {rep.get('admission_pct', 'n/a')} % overall |
| Dafny admission | n/a | {adm('dafny')} |
| Lean admission | n/a | {adm('lean')} |
| Verus admission | 0 % | {adm('verus')} (toolchain unavailable) |
| Use | raw dataset / negative-result section only | Phase 9 evaluation set |

Dafny + Lean combined admission (v2): **{dl_pct} %**.

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
"""
    Path("docs/phase5_to_phase8_complete.md").write_text(md)
    print("wrote docs/phase5_to_phase8_complete.md")
    print(f"v1: {v1_main}+{v1_xf}  v2: {v2_main}+{v2_xf}  DL_admission={dl_pct}%")


if __name__ == "__main__":
    main()
