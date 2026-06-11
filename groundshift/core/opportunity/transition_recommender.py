from __future__ import annotations

from groundshift.models.transition_result import TransitionResult, TransitionSuggestion


def _jaccard_overlap(min1: float, max1: float, min2: float, max2: float) -> float:
    intersection = max(0.0, min(max1, max2) - max(min1, min2))
    union = max(max1, max2) - min(min1, min2)
    return intersection / union if union > 0 else 0.0


def _envelope_overlap(current: dict, candidate: dict) -> float:
    current_thresholds = current["climate_envelope"]["thresholds"]
    candidate_thresholds = candidate["climate_envelope"]["thresholds"]
    shared = set(current_thresholds) & set(candidate_thresholds)
    if not shared:
        return 0.0
    scores = [
        _jaccard_overlap(
            current_thresholds[var]["viable_min"],
            current_thresholds[var]["viable_max"],
            candidate_thresholds[var]["viable_min"],
            candidate_thresholds[var]["viable_max"],
        )
        for var in shared
    ]
    return sum(scores) / len(scores)


class TransitionRecommender:
    def __init__(self, candidates: list[dict]):
        self._candidates = candidates

    def recommend(self, current_profile: dict) -> TransitionResult:
        current_id = current_profile["crop_id"]
        suggestions = [
            TransitionSuggestion(
                crop_id=c["crop_id"],
                crop_name=c["name"],
                overlap_score=_envelope_overlap(current_profile, c),
            )
            for c in self._candidates
            if c["crop_id"] != current_id
        ]
        suggestions.sort(key=lambda s: s.overlap_score, reverse=True)
        return TransitionResult(suggestions=suggestions)
