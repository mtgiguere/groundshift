from groundshift.core.envelope.scorer import EnvelopeScorer
from groundshift.core.envelope.threshold import ClimateThreshold


def envelope_scorer_from_profile(profile: dict) -> EnvelopeScorer:
    thresholds = {
        name: ClimateThreshold(
            viable_min=t["viable_min"],
            optimal_min=t["optimal_min"],
            optimal_max=t["optimal_max"],
            viable_max=t["viable_max"],
        )
        for name, t in profile["climate_envelope"]["thresholds"].items()
    }
    return EnvelopeScorer(thresholds)
