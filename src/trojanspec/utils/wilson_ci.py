"""Wilson score interval for a binomial proportion.

Every detection rate in TrojanSpec-Bench is reported with a Wilson 95% CI.
No bare percentages.
"""

from __future__ import annotations

import math

from scipy.stats import norm


def wilson_ci(successes: int, trials: int, confidence: float = 0.95) -> tuple[float, float]:
    """Return ``(low, high)`` Wilson score bounds for ``successes / trials``.

    Returns ``(0.0, 1.0)`` for an empty sample.
    """
    if trials <= 0:
        return (0.0, 1.0)
    if successes < 0 or successes > trials:
        raise ValueError(f"successes={successes} out of range for trials={trials}")

    z = norm.ppf(1 - (1 - confidence) / 2)
    p = successes / trials
    n = trials
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))
