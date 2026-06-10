from groundshift.core.envelope.climate_envelope import compute_envelope
from groundshift.core.envelope.climate_source import ClimateDataSource
from groundshift.core.scorer import Scorer
from groundshift.models.bounding_box import BoundingBox
from groundshift.models.suitability_result import SuitabilityResult
from groundshift.models.time_range import TimeRange
from groundshift.plugins.registry import PluginRegistry


class DescribePhaseRunner:
    def __init__(self, climate_source: ClimateDataSource, registry: PluginRegistry) -> None:
        self._source = climate_source
        self._scorer = Scorer(registry)

    def run(self, profile: dict, region: BoundingBox, time_range: TimeRange) -> SuitabilityResult:
        envelope = compute_envelope(profile, self._source, region, time_range)
        return self._scorer.run(envelope, region, time_range, profile)
