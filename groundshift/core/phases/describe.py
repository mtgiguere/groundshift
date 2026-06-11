from __future__ import annotations

from groundshift.core.envelope.climate_envelope import compute_envelope
from groundshift.core.envelope.climate_source import ClimateDataSource
from groundshift.core.imagery.divergence import compute_divergence
from groundshift.core.imagery.imagery_source import ImagerySource
from groundshift.core.scorer import Scorer
from groundshift.models.bounding_box import BoundingBox
from groundshift.models.describe_result import DescribeResult
from groundshift.models.time_range import TimeRange
from groundshift.models.trend_result import TrendResult
from groundshift.plugins.registry import PluginRegistry


class DescribePhaseRunner:
    def __init__(
        self,
        climate_source: ClimateDataSource,
        registry: PluginRegistry,
        imagery_source: ImagerySource | None = None,
        landsat_source: ImagerySource | None = None,
    ) -> None:
        self._source = climate_source
        self._scorer = Scorer(registry)
        self._imagery_source = imagery_source
        self._landsat_source = landsat_source

    def run(self, profile: dict, region: BoundingBox, time_range: TimeRange) -> DescribeResult:
        envelope = compute_envelope(profile, self._source, region, time_range)
        suitability = self._scorer.run(envelope, region, time_range, profile)
        divergence = None
        if self._imagery_source is not None:
            ndvi = self._imagery_source.fetch("ndvi", region, time_range)
            divergence = compute_divergence(suitability, ndvi)
        trend = None
        if self._landsat_source is not None:
            slope = self._landsat_source.fetch("ndvi_trend", region, time_range)
            trend = TrendResult(slope=slope)
        return DescribeResult(suitability=suitability, divergence=divergence, trend=trend)
