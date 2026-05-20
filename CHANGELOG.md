# Changelog

## v0.4.1 — 2026-05-20
- Phase 14 head-to-head with MutDafny (Amaral, Mendes, Campos — arXiv:2511.15403, ICSE 2026)
  on the 319 admitted Dafny triples: ours F1 0.540, MutDafny F1 0.530 (statistical tie,
  McNemar p=0.895), atomic_monitor K=2 F1 0.992 (strict superset of MutDafny on trojan side,
  McNemar p<10⁻⁶¹). Mutation-based detection has a structural ceiling — vacuity OR
  implementation_leak, not both; blind to domain_restriction and predicate_swap.
- New: `scripts/install_mutdafny.sh`, `scripts/run_phase14.sh`, `scripts/14_mutdafny_*.py`,
  `data/phase14_*` raw results, `docs/mutdafny_comparison.md` (paper-section writeup),
  `MUTDAFNY_COMPARISON.md` (full investigation log).
- Reproducible end-to-end from a fresh clone in ~75 min, $0 Bedrock (toolchain only).

## v0.4.0 — 2026-05-20
- Phase 11 Mathlib calibration extended to atomic_monitor (K=2 of 4)
- atomic_monitor promoted to src/trojanspec/specguard/ as library module
- Reproducibility: .env.example now declares required AWS_* variables
- Docs: version strings reconciled across pyproject / HANDOFF / tag

## v0.3.0 — 2026-05-20
- HuggingFace dataset release (m-zest/trojanspec-bench)
- HuggingFace Space demo (m-zest/specguard-demo)
- Phase 12/13 rows added to README/STATUS/HANDOFF

## v0.2.0 — earlier
- Phase 10i atomic-criteria monitor (F1 0.967)
- Phase 10h beat-SSC ablation (5 hypotheses)
