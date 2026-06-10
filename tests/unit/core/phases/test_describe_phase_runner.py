from datetime import datetime

import numpy as np
import xarray as xr

from groundshift.core.envelope.climate_source import ClimateDataSource
from groundshift.models.bounding_box import BoundingBox
from groundshift.models.suitability_result import SuitabilityResult
from groundshift.models.time_range import TimeRange
from groundshift.plugins.registry import PluginRegistry

REGION = BoundingBox(min_lon=35.0, min_lat=3.0, max_lon=42.0, max_lat=15.0)
TIME_RANGE = TimeRange(start=datetime(2020, 1, 1), end=datetime(2021, 1, 1))

_PROFILE = {
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


class _ConstantSource(ClimateDataSource):
    def __init__(self, values: dict[str, float]) -> None:
        self._values = values

    def fetch(self, variable: str, region: BoundingBox, time_range: TimeRange) -> xr.DataArray:
        return xr.DataArray(np.full((4, 4), self._values[variable]))


def _make_runner(source: ClimateDataSource, registry: PluginRegistry | None = None):
    from groundshift.core.phases.describe import DescribePhaseRunner

    return DescribePhaseRunner(source, registry or PluginRegistry())


def test_describe_phase_runner_returns_suitability_result():
    source = _ConstantSource({"mean_annual_temp_c": 21.0, "annual_precipitation_mm": 2000.0})
    runner = _make_runner(source)
    result = runner.run(_PROFILE, REGION, TIME_RANGE)
    assert isinstance(result, SuitabilityResult)


def test_describe_phase_runner_result_fields_are_dataarrays():
    source = _ConstantSource({"mean_annual_temp_c": 21.0, "annual_precipitation_mm": 2000.0})
    runner = _make_runner(source)
    result = runner.run(_PROFILE, REGION, TIME_RANGE)
    assert isinstance(result.score, xr.DataArray)
    assert isinstance(result.confidence, xr.DataArray)


def test_describe_phase_runner_optimal_climate_no_plugins_scores_one():
    source = _ConstantSource({"mean_annual_temp_c": 21.0, "annual_precipitation_mm": 2000.0})
    runner = _make_runner(source)
    result = runner.run(_PROFILE, REGION, TIME_RANGE)
    import pytest
    assert float(result.score.mean()) == pytest.approx(1.0)


def test_describe_phase_runner_impossible_climate_scores_zero():
    source = _ConstantSource({"mean_annual_temp_c": 5.0, "annual_precipitation_mm": 2000.0})
    runner = _make_runner(source)
    result = runner.run(_PROFILE, REGION, TIME_RANGE)
    import pytest
    assert float(result.score.mean()) == pytest.approx(0.0)


def test_describe_phase_runner_passes_envelope_as_gate_to_scorer():
    """Envelope zero must produce zero final score even if plugins would push higher."""
    from groundshift.models.suitability_modifier import SuitabilityModifier
    from groundshift.plugins.base import GroundshiftPlugin
    from groundshift.models.layer_data import LayerData
    from groundshift.models.plugin_metadata import PluginMetadata

    class _OptimisticPlugin(GroundshiftPlugin):
        """Always returns a perfect-score modifier regardless of climate."""

        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                plugin_id="optimistic",
                name="Optimistic",
                version="0.1.0",
                description="Always happy",
                author="test",
                compatible_crops=["coffee_arabica"],
                data_sources=[],
                requires_network=False,
                phase_applicability=["describe"],
                threat_tier="stress",
            )

        def validate_config(self, crop_profile: dict) -> bool:
            return True

        def fetch_data(self, region: BoundingBox, time_range: TimeRange) -> LayerData:
            return LayerData(
                plugin_id="optimistic",
                region=region,
                time_range=time_range,
                data=xr.DataArray(np.ones((4, 4))),
                metadata={},
            )

        def describe(self, score: SuitabilityModifier) -> str:
            return "optimistic"

        def score(self, layer: LayerData, crop_profile: dict) -> SuitabilityModifier:
            ones = xr.DataArray(np.ones((4, 4)))
            return SuitabilityModifier(
                plugin_id="optimistic",
                region=layer.region,
                factor_value=ones,
                probability=ones,
                confidence=ones,
                metadata={"threat_tier": "stress"},
            )

    registry = PluginRegistry()
    registry.register(_OptimisticPlugin())
    source = _ConstantSource({"mean_annual_temp_c": 5.0, "annual_precipitation_mm": 2000.0})
    runner = _make_runner(source, registry)
    result = runner.run(_PROFILE, REGION, TIME_RANGE)

    import pytest
    assert float(result.score.mean()) == pytest.approx(0.0)
