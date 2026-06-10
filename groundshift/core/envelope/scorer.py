from groundshift.core.envelope.threshold import ClimateThreshold


class EnvelopeScorer:
    def __init__(self, thresholds: dict[str, ClimateThreshold]) -> None:
        self._thresholds = thresholds

    def score(self, values: dict[str, float]) -> float:
        return min(t.score(values[name]) for name, t in self._thresholds.items())
