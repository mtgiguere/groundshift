import pytest
from hypothesis import given
from hypothesis import strategies as st

from groundshift.core.envelope.threshold import ClimateThreshold


def test_threshold_stores_boundaries():
    t = ClimateThreshold(viable_min=15.0, optimal_min=18.0, optimal_max=24.0, viable_max=30.0)
    assert t.viable_min == 15.0
    assert t.optimal_min == 18.0
    assert t.optimal_max == 24.0
    assert t.viable_max == 30.0


@pytest.mark.parametrize(
    "kwargs,match",
    [
        (
            {"viable_min": 20.0, "optimal_min": 18.0, "optimal_max": 24.0, "viable_max": 30.0},
            "viable_min",
        ),
        (
            {"viable_min": 15.0, "optimal_min": 25.0, "optimal_max": 24.0, "viable_max": 30.0},
            "optimal_min",
        ),
        (
            {"viable_min": 15.0, "optimal_min": 18.0, "optimal_max": 31.0, "viable_max": 30.0},
            "optimal_max",
        ),
    ],
)
def test_threshold_raises_if_boundaries_out_of_order(kwargs, match):
    with pytest.raises(ValueError, match=match):
        ClimateThreshold(**kwargs)


_COFFEE_TEMP = ClimateThreshold(
    viable_min=15.0, optimal_min=18.0, optimal_max=24.0, viable_max=30.0
)


def test_threshold_scores_below_viable_min_as_zero():
    assert _COFFEE_TEMP.score(14.9) == 0.0


def test_threshold_scores_above_viable_max_as_zero():
    assert _COFFEE_TEMP.score(30.1) == 0.0


def test_threshold_scores_optimal_range_as_one():
    assert _COFFEE_TEMP.score(21.0) == 1.0


def test_threshold_lower_ramp_scores_linearly():
    # midpoint of lower ramp [15, 18] is 16.5 → score = (16.5-15)/(18-15) = 0.5
    assert abs(_COFFEE_TEMP.score(16.5) - 0.5) < 1e-9


def test_threshold_upper_ramp_scores_linearly():
    # midpoint of upper ramp [24, 30] is 27.0 → score = (30-27)/(30-24) = 0.5
    assert abs(_COFFEE_TEMP.score(27.0) - 0.5) < 1e-9


@pytest.mark.parametrize(
    "value,expected",
    [
        (15.0, 0.0),  # viable_min — bottom of lower ramp
        (18.0, 1.0),  # optimal_min — top of lower ramp
        (24.0, 1.0),  # optimal_max — top of upper ramp
        (30.0, 0.0),  # viable_max — bottom of upper ramp
    ],
)
def test_threshold_boundary_values(value, expected):
    assert _COFFEE_TEMP.score(value) == expected


def test_threshold_with_no_lower_ramp_scores_viable_min_as_zero():
    # viable_min == optimal_min means no lower transition — viable_min itself scores 0
    t = ClimateThreshold(viable_min=18.0, optimal_min=18.0, optimal_max=24.0, viable_max=30.0)
    assert t.score(18.0) == 1.0
    assert t.score(17.9) == 0.0


def test_threshold_with_no_upper_ramp_scores_viable_max_as_zero():
    t = ClimateThreshold(viable_min=15.0, optimal_min=18.0, optimal_max=30.0, viable_max=30.0)
    assert t.score(30.0) == 1.0
    assert t.score(30.1) == 0.0


@given(
    viable_min=st.floats(-50.0, 0.0, allow_nan=False),
    optimal_width=st.floats(1.0, 10.0, allow_nan=False),
    optimal_span=st.floats(1.0, 10.0, allow_nan=False),
    upper_margin=st.floats(1.0, 10.0, allow_nan=False),
    value=st.floats(-60.0, 60.0, allow_nan=False),
)
def test_threshold_score_always_in_0_1(
    viable_min, optimal_width, optimal_span, upper_margin, value
):
    optimal_min = viable_min + optimal_width
    optimal_max = optimal_min + optimal_span
    viable_max = optimal_max + upper_margin
    t = ClimateThreshold(
        viable_min=viable_min,
        optimal_min=optimal_min,
        optimal_max=optimal_max,
        viable_max=viable_max,
    )
    assert 0.0 <= t.score(value) <= 1.0
