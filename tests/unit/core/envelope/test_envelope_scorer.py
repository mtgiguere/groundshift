import pytest

from groundshift.core.envelope.scorer import EnvelopeScorer
from groundshift.core.envelope.threshold import ClimateThreshold

_TEMP = ClimateThreshold(viable_min=15.0, optimal_min=18.0, optimal_max=24.0, viable_max=30.0)
_RAIN = ClimateThreshold(
    viable_min=1200.0, optimal_min=1500.0, optimal_max=2500.0, viable_max=3000.0
)


def test_single_variable_in_optimal_range_scores_one():
    scorer = EnvelopeScorer({"temp": _TEMP})
    assert scorer.score({"temp": 21.0}) == 1.0


def test_single_variable_outside_viable_range_scores_zero():
    scorer = EnvelopeScorer({"temp": _TEMP})
    assert scorer.score({"temp": 5.0}) == 0.0


def test_score_is_limited_by_worst_variable():
    # temp is optimal (1.0), rainfall is below viable (0.0) → overall must be 0.0
    scorer = EnvelopeScorer({"temp": _TEMP, "rain": _RAIN})
    assert scorer.score({"temp": 21.0, "rain": 500.0}) == 0.0


def test_all_variables_optimal_scores_one():
    scorer = EnvelopeScorer({"temp": _TEMP, "rain": _RAIN})
    assert scorer.score({"temp": 21.0, "rain": 2000.0}) == 1.0


def test_score_raises_if_value_missing_for_threshold():
    scorer = EnvelopeScorer({"temp": _TEMP, "rain": _RAIN})
    with pytest.raises(KeyError):
        scorer.score({"temp": 21.0})


@pytest.mark.parametrize(
    "temp,rain",
    [
        (21.0, 500.0),  # rain kills it
        (10.0, 2000.0),  # temp kills it
        (16.5, 1350.0),  # both on lower ramp — score = min(0.5, 0.5) = 0.5
    ],
)
def test_score_minimum_of_all_variables(temp, rain):
    scorer = EnvelopeScorer({"temp": _TEMP, "rain": _RAIN})
    expected = min(_TEMP.score(temp), _RAIN.score(rain))
    assert abs(scorer.score({"temp": temp, "rain": rain}) - expected) < 1e-9
