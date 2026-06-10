import pytest

from groundshift.core.envelope.profile_loader import envelope_scorer_from_profile
from groundshift.core.envelope.scorer import EnvelopeScorer

_MINIMAL_PROFILE = {
    "crop_id": "coffee_arabica",
    "climate_envelope": {
        "thresholds": {
            "mean_annual_temp_c": {
                "viable_min": 15.0,
                "optimal_min": 18.0,
                "optimal_max": 24.0,
                "viable_max": 30.0,
            }
        }
    },
}

_TWO_VARIABLE_PROFILE = {
    "crop_id": "coffee_arabica",
    "climate_envelope": {
        "thresholds": {
            "mean_annual_temp_c": {
                "viable_min": 15.0,
                "optimal_min": 18.0,
                "optimal_max": 24.0,
                "viable_max": 30.0,
            },
            "annual_precipitation_mm": {
                "viable_min": 1200.0,
                "optimal_min": 1500.0,
                "optimal_max": 2500.0,
                "viable_max": 3000.0,
            },
        }
    },
}


def test_returns_envelope_scorer():
    result = envelope_scorer_from_profile(_MINIMAL_PROFILE)
    assert isinstance(result, EnvelopeScorer)


def test_two_variable_profile_builds_scorer_with_both_thresholds():
    scorer = envelope_scorer_from_profile(_TWO_VARIABLE_PROFILE)
    score = scorer.score({"mean_annual_temp_c": 21.0, "annual_precipitation_mm": 2000.0})
    assert score == 1.0


def test_missing_climate_envelope_raises():
    with pytest.raises(KeyError):
        envelope_scorer_from_profile({"crop_id": "coffee_arabica"})
