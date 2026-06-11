from __future__ import annotations

from groundshift.core.envelope.climate_envelope import compute_envelope
from groundshift.core.envelope.climate_source import ClimateDataSource
from groundshift.core.scorer import Scorer
from groundshift.models.bounding_box import BoundingBox
from groundshift.models.predict_result import PredictProjection, PredictResult
from groundshift.models.time_range import TimeRange
from groundshift.plugins.registry import PluginRegistry


class PredictPhaseRunner:
    def __init__(
        self,
        climate_source: ClimateDataSource,
        registry: PluginRegistry,
        scenarios: list[str],
        horizons: list[int],
    ) -> None:
        self._source = climate_source
        self._scorer = Scorer(registry)
        self._scenarios = scenarios
        self._horizons = horizons

    def run(self, profile: dict, region: BoundingBox, time_range: TimeRange) -> PredictResult:
        projections = []
        for scenario in self._scenarios:
            for horizon in self._horizons:
                tr = TimeRange(
                    start=time_range.start,
                    end=time_range.end,
                    scenario=scenario,
                    horizon_year=horizon,
                )
                envelope = compute_envelope(profile, self._source, region, tr)
                suitability = self._scorer.run(envelope, region, tr, profile)
                projections.append(
                    PredictProjection(
                        scenario=scenario, horizon_year=horizon, suitability=suitability
                    )
                )
        return PredictResult(projections=projections)
