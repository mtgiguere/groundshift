import functools

import numpy as np
import xarray as xr

from groundshift.core.envelope.threshold import ClimateThreshold


class EnvelopeScorer:
    def __init__(self, thresholds: dict[str, ClimateThreshold]) -> None:
        self._thresholds = thresholds

    def score(self, values: dict[str, float | xr.DataArray]) -> float | xr.DataArray:
        scores = [t.score(values[name]) for name, t in self._thresholds.items()]
        return functools.reduce(np.minimum, scores)
