# Changelog

## v0.4.2 - 2026-05-24

- README polish: cleaner structure, table of contents, six-detector
  comparison table, deployment rationale for atomic K=2 over C3 alone,
  Phase 14 row added to the headline results table.
- `paper/` directory added with LaTeX source, Makefile, and the v0.4.1
  submission PDF. Build from a fresh clone with `cd paper && make paper`.
- `PAPER_AUDIT.md` added at repo root: every numerical claim in the paper
  is cross-referenced to a JSON file in `data/`. 20 corrections logged
  versus the v0.4.0 paper draft.
- Documentation consistency pass: McNemar p-value corrected to p < 10^-45
  (precise: 2.8 x 10^-46, derived from chi-squared = 204 on 1 d.f. via
  mpmath gammainc); detector count harmonised at six across all docs.
- HuggingFace Space (m-zest/specguard-demo): pre-loaded examples fixed,
  UI polished, version footer bumped to v0.4.1, graceful error handling
  with show_error=True surfaces real Bedrock errors instead of silent
  failures.
- HuggingFace Dataset (m-zest/trojanspec-bench): v0.4.1 changelog entry
  added with Phase 11 atomic Mathlib calibration and Phase 14 MutDafny
  head-to-head.
- No changes to detector code, dataset parquet, or verifier admission
  results. Same 1,024 admitted triples, same six detectors, same headline
  F1 numbers.

## v0.4.1 - 2026-05-20

- Phase 14 head-to-head with MutDafny (Amaral, Mendes, Campos.
  arXiv:2511.15403, ICSE 2026) on the 319 admitted Dafny triples. Our
  static mutation_coverage F1 0.540, MutDafny F1 0.530 (statistical tie,
  McNemar p = 0.895). atomic_monitor K=2 F1 0.992 is a strict superset
  of MutDafny on the trojan side (McNemar p < 10^-45). Mutation-based
  detection has a structural ceiling: it catches either vacuity or
  implementation_leak but not both, and is blind to domain_restriction
  and predicate_swap.
- New artifacts: `scripts/install_mutdafny.sh`, `scripts/run_phase14.sh`,
  `scripts/14_mutdafny_*.py`, `data/phase14_*` raw results,
  `docs/mutdafny_comparison.md` (paper-section writeup),
  `MUTDAFNY_COMPARISON.md` (full investigation log).
- Reproducible end-to-end from a fresh clone in ~75 min at $0 Bedrock
  cost (toolchain only).

## v0.4.0 - 2026-05-20

- Phase 11 Mathlib calibration extended to atomic_monitor (K = 2 of 4):
  3/100 false positive rate on 100 honest Lean lemmas, a 7.7x reduction
  over monitor_consensus (23/100). The three atomic flags are a strict
  subset of the consensus flags.
- atomic_monitor promoted to library module at
  `src/trojanspec/specguard/atomic_monitor.py` with unit tests.
- Reproducibility: `.env.example` now declares required AWS_* variables.
- Documentation: version strings reconciled across pyproject.toml,
  HANDOFF.md, and the v0.4.0 tag.

## v0.3.0 - 2026-05-20

- HuggingFace dataset release: `m-zest/trojanspec-bench`.
- HuggingFace Space demo: `m-zest/specguard-demo`.
- Phase 12 (demo) and Phase 13 (dataset release) rows added to
  README.md, STATUS.md, and HANDOFF.md.

## v0.2.0 - earlier

- Phase 10i atomic-criteria monitor (F1 0.967, the headline result).
- Phase 10h beat-SSC ablation: five hypotheses tested, all tied SSC.
