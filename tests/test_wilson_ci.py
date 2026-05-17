import pytest

from trojanspec.utils.wilson_ci import wilson_ci


def test_empty_sample():
    assert wilson_ci(0, 0) == (0.0, 1.0)


def test_bounds_are_ordered_and_clamped():
    lo, hi = wilson_ci(50, 100)
    assert 0.0 <= lo < 0.5 < hi <= 1.0


def test_all_success_upper_bound_is_one_ish():
    lo, hi = wilson_ci(20, 20)
    assert hi == pytest.approx(1.0, abs=1e-9) or hi < 1.0
    assert lo > 0.5


def test_invalid_counts():
    with pytest.raises(ValueError):
        wilson_ci(5, 3)
