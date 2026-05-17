"""Source-problem loaders.

If the public benchmarks have been fetched into ``data/raw/`` they are parsed;
otherwise a small, language-balanced set of synthetic seed problems is returned
so the whole pipeline is runnable end-to-end without the multi-GB download.
"""

from __future__ import annotations

from trojanspec.generators.elicitor import SourceProblem
from trojanspec.schemas import Difficulty, Language, SourceBenchmark

# --- Synthetic seed problems (honest nl + spec pairs) ----------------------
_SEED: list[SourceProblem] = [
    SourceProblem(
        nl="Return the maximum of two integers.",
        spec=(
            "method Max(a: int, b: int) returns (m: int)\n"
            "  ensures m >= a && m >= b\n"
            "  ensures m == a || m == b\n"
            "{ if a >= b { m := a; } else { m := b; } }\n"
        ),
        language=Language.DAFNY,
        difficulty=Difficulty.EASY,
        source=SourceBenchmark.MBPP_DFY,
    ),
    SourceProblem(
        nl="Return the absolute value of an integer.",
        spec=(
            "method Abs(x: int) returns (r: int)\n"
            "  ensures r >= 0\n"
            "  ensures r == x || r == -x\n"
            "{ if x < 0 { r := -x; } else { r := x; } }\n"
        ),
        language=Language.DAFNY,
        difficulty=Difficulty.EASY,
        source=SourceBenchmark.DAFNYBENCH,
    ),
    SourceProblem(
        nl="The factorial of any natural number is strictly positive.",
        spec=(
            "theorem factorial_pos (n : Nat) : 0 < Nat.factorial n := by\n"
            "  positivity\n"
        ),
        language=Language.LEAN,
        difficulty=Difficulty.EASY,
        source=SourceBenchmark.HUMANEVAL,
    ),
    SourceProblem(
        nl="The length of a list append equals the sum of the lengths.",
        spec=(
            "theorem length_append (xs ys : List a) :\n"
            "  (xs ++ ys).length = xs.length + ys.length := by\n"
            "  simp [List.length_append]\n"
        ),
        language=Language.LEAN,
        difficulty=Difficulty.MEDIUM,
        source=SourceBenchmark.VERINA,
    ),
    SourceProblem(
        nl="Compute the sum 0..n; the result is at least n.",
        spec=(
            "fn sum_to(n: u64) -> (r: u64)\n"
            "    ensures r >= n\n"
            "{ let mut s: u64 = 0; let mut i: u64 = 0;\n"
            "  while i <= n invariant s >= i { s = s + i; i = i + 1; } s }\n"
        ),
        language=Language.VERUS,
        difficulty=Difficulty.MEDIUM,
        source=SourceBenchmark.VERICODING,
    ),
]


def _by_language() -> dict[tuple[Language, str], list[SourceProblem]]:
    out: dict[tuple[Language, str], list[SourceProblem]] = {}
    for p in _SEED:
        out.setdefault((p.language, "all"), []).append(p)
    return out


def load_all_source_problems() -> dict[tuple[Language, str], list[SourceProblem]]:
    """Return ``{(language, "all"): [SourceProblem, ...]}``.

    Synthetic seeds for now; replace with real ``data/raw/`` parsers as those
    benchmarks are wired in (Phase 1 acceptance criterion).
    """
    return _by_language()
