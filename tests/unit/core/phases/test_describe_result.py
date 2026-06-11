from datetime import datetime

import numpy as np
import pytest
import xarray as xr

from groundshift.core.envelope.climate_source import ClimateDataSource
from groundshift.core.imagery.imagery_source import ImagerySource
from groundshift.models.bounding_box import BoundingBox
from groundshift.models.divergence_result import DivergenceResult
from groundshift.models.suitability_result import SuitabilityResult
from groundshift.models.time_range import TimeRange

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


_CLIMATE_VALUES = {"mean_annual_temp_c": 21.0, "annual_precipitation_mm": 2000.0}


class _ConstantClimateSource(ClimateDataSource):
    def fetch(self, variable: str, region: BoundingBox, time_range: TimeRange) -> xr.DataArray:
        return xr.DataArray(np.full((4, 4), _CLIMATE_VALUES[variable]))


class _ConstantImagerySource(ImagerySource):
    def __init__(self, ndvi_val: float) -> None:
        self._val = ndvi_val

    def fetch(self, variable: str, region: BoundingBox, time_range: TimeRange) -> xr.DataArray:
        return xr.DataArray(np.full((4, 4), self._val, dtype="float32"))


def _make_runner(imagery_source=None):
    from groundshift.core.phases.describe import DescribePhaseRunner
    from groundshift.plugins.registry import PluginRegistry

    return DescribePhaseRunner(
        _ConstantClimateSource(),
        PluginRegistry(),
        imagery_source=imagery_source,
    )


def test_describe_result_has_suitability_field():
    from groundshift.models.describe_result import DescribeResult

    runner = _make_runner()
    result = runner.run(_PROFILE, REGION, TIME_RANGE)
    assert isinstance(result, DescribeResult)
    assert isinstance(result.suitability, SuitabilityResult)


def test_describe_result_without_imagery_has_none_divergence():
    runner = _make_runner()
    result = runner.run(_PROFILE, REGION, TIME_RANGE)
    assert result.divergence is None


def test_describe_result_with_imagery_has_divergence_result():
    runner = _make_runner(imagery_source=_ConstantImagerySource(0.5))
    result = runner.run(_PROFILE, REGION, TIME_RANGE)
    assert isinstance(result.divergence, DivergenceResult)
    assert isinstance(result.divergence.surface, xr.DataArray)


def test_describe_result_suitability_score_unchanged_by_imagery():
    # Imagery adds a divergence signal but must NOT modify the climate score.
    runner_no_imagery = _make_runner()
    runner_with_imagery = _make_runner(imagery_source=_ConstantImagerySource(0.3))
    result_plain = runner_no_imagery.run(_PROFILE, REGION, TIME_RANGE)
    result_imagery = runner_with_imagery.run(_PROFILE, REGION, TIME_RANGE)
    assert float(result_plain.suitability.score.mean()) == pytest.approx(
        float(result_imagery.suitability.score.mean())
    )
