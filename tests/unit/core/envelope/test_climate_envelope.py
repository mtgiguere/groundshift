from datetime import datetime

import numpy as np
import pytest
import xarray as xr

from groundshift.core.envelope.climate_envelope import compute_envelope
from groundshift.core.envelope.climate_source import ClimateDataSource
from groundshift.models.bounding_box import BoundingBox
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


class _ConstantSource(ClimateDataSource):
    """Returns a uniform grid of a fixed value for each named variable."""

    def __init__(self, values: dict[str, float]) -> None:
        self._values = values

    def fetch(self, variable: str, region: BoundingBox, time_range: TimeRange) -> xr.DataArray:
        return xr.DataArray(np.full((4, 4), self._values[variable]))


def test_compute_envelope_returns_dataarray():
    source = _ConstantSource({"mean_annual_temp_c": 21.0, "annual_precipitation_mm": 2000.0})
    result = compute_envelope(_PROFILE, source, REGION, TIME_RANGE)
    assert isinstance(result, xr.DataArray)


def test_compute_envelope_optimal_climate_scores_one():
    source = _ConstantSource({"mean_annual_temp_c": 21.0, "annual_precipitation_mm": 2000.0})
    result = compute_envelope(_PROFILE, source, REGION, TIME_RANGE)
    assert float(result.mean()) == pytest.approx(1.0)


def test_compute_envelope_impossible_temp_scores_zero():
    source = _ConstantSource({"mean_annual_temp_c": 5.0, "annual_precipitation_mm": 2000.0})
    result = compute_envelope(_PROFILE, source, REGION, TIME_RANGE)
    assert float(result.mean()) == pytest.approx(0.0)


def test_compute_envelope_applies_liebig_min():
    # Temp optimal, precip below viable → envelope = 0.0
    source = _ConstantSource({"mean_annual_temp_c": 21.0, "annual_precipitation_mm": 100.0})
    result = compute_envelope(_PROFILE, source, REGION, TIME_RANGE)
    assert float(result.mean()) == pytest.approx(0.0)


def test_compute_envelope_partial_score_reflects_worst_variable():
    # Temp on lower ramp (score=0.5), precip optimal (score=1.0) → min=0.5
    source = _ConstantSource({"mean_annual_temp_c": 16.5, "annual_precipitation_mm": 2000.0})
    result = compute_envelope(_PROFILE, source, REGION, TIME_RANGE)
    assert float(result.mean()) == pytest.approx(0.5)


def test_compute_envelope_raises_on_unknown_source_variable():
    source = _ConstantSource({"mean_annual_temp_c": 21.0})  # missing precipitation
    with pytest.raises(KeyError):
        compute_envelope(_PROFILE, source, REGION, TIME_RANGE)
