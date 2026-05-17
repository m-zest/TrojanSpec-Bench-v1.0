"""TrojanSpec-Bench: adversarial specification elicitation for AI-assisted
formal verification (Dafny, Lean 4, Verus)."""

from trojanspec.schemas import (
    AttackPattern,
    CryptoPrimitive,
    Difficulty,
    Language,
    SourceBenchmark,
    Triple,
)

__version__ = "1.0.0"

__all__ = [
    "AttackPattern",
    "CryptoPrimitive",
    "Difficulty",
    "Language",
    "SourceBenchmark",
    "Triple",
    "__version__",
]
