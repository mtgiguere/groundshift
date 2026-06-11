import pytest

from groundshift.core.opportunity.transition_recommender import TransitionRecommender
from groundshift.models.transition_result import TransitionResult


def _profile(crop_id, temp_min, temp_max, precip_min=None, precip_max=None):
    thresholds = {
        "mean_annual_temp_c": {
            "viable_min": temp_min,
            "optimal_min": temp_min + 2,
            "optimal_max": temp_max - 2,
            "viable_max": temp_max,
        }
    }
    if precip_min is not None:
        thresholds["annual_precipitation_mm"] = {
            "viable_min": precip_min,
            "optimal_min": precip_min + 100,
            "optimal_max": precip_max - 100,
            "viable_max": precip_max,
        }
    return {
        "crop_id": crop_id,
        "name": crop_id.title(),
        "climate_envelope": {"thresholds": thresholds},
    }


_COFFEE = _profile("coffee", temp_min=15.0, temp_max=30.0, precip_min=1200.0, precip_max=3000.0)
_IDENTICAL = _profile("tea", temp_min=15.0, temp_max=30.0, precip_min=1200.0, precip_max=3000.0)
_NO_OVERLAP = _profile("wheat", temp_min=0.0, temp_max=5.0)
_PARTIAL = _profile("cocoa", temp_min=20.0, temp_max=35.0)


class TestTransitionRecommender:
    def test_returns_transition_result(self):
        result = TransitionRecommender([_IDENTICAL]).recommend(_COFFEE)
        assert isinstance(result, TransitionResult)

    def test_result_has_suggestions_list(self):
        result = TransitionRecommender([_IDENTICAL]).recommend(_COFFEE)
        assert hasattr(result, "suggestions")
        assert isinstance(result.suggestions, list)

    def test_excludes_current_crop_by_id(self):
        same_id = _profile("coffee", temp_min=15.0, temp_max=30.0)
        result = TransitionRecommender([same_id]).recommend(_COFFEE)
        ids = [s.crop_id for s in result.suggestions]
        assert "coffee" not in ids

    def test_includes_other_crops(self):
        result = TransitionRecommender([_IDENTICAL, _NO_OVERLAP]).recommend(_COFFEE)
        ids = {s.crop_id for s in result.suggestions}
        assert "tea" in ids
        assert "wheat" in ids

    def test_identical_envelope_scores_1(self):
        result = TransitionRecommender([_IDENTICAL]).recommend(_COFFEE)
        assert result.suggestions[0].overlap_score == pytest.approx(1.0)

    def test_no_overlap_scores_0(self):
        result = TransitionRecommender([_NO_OVERLAP]).recommend(_COFFEE)
        assert result.suggestions[0].overlap_score == pytest.approx(0.0)

    def test_partial_overlap_between_0_and_1(self):
        result = TransitionRecommender([_PARTIAL]).recommend(_COFFEE)
        score = result.suggestions[0].overlap_score
        assert 0.0 < score < 1.0

    def test_sorted_descending_by_overlap_score(self):
        result = TransitionRecommender([_NO_OVERLAP, _IDENTICAL, _PARTIAL]).recommend(_COFFEE)
        scores = [s.overlap_score for s in result.suggestions]
        assert scores == sorted(scores, reverse=True)

    def test_overlap_score_bounded_0_to_1(self):
        result = TransitionRecommender([_IDENTICAL, _NO_OVERLAP, _PARTIAL]).recommend(_COFFEE)
        for s in result.suggestions:
            assert 0.0 <= s.overlap_score <= 1.0

    def test_suggestion_has_crop_id_and_name(self):
        result = TransitionRecommender([_IDENTICAL]).recommend(_COFFEE)
        s = result.suggestions[0]
        assert s.crop_id == "tea"
        assert s.crop_name == "Tea"

    def test_empty_candidates_returns_empty_suggestions(self):
        result = TransitionRecommender([]).recommend(_COFFEE)
        assert result.suggestions == []

    def test_candidates_list_with_only_current_crop_returns_empty(self):
        result = TransitionRecommender([_COFFEE]).recommend(_COFFEE)
        assert result.suggestions == []
