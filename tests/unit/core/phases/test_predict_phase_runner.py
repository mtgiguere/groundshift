from datetime import datetime

import numpy as np
import xarray as xr

from groundshift.core.envelope.climate_source import ClimateDataSource
from groundshift.models.bounding_box import BoundingBox
from groundshift.models.predict_result import PredictProjection, PredictResult
from groundshift.models.suitability_result import SuitabilityResult
from groundshift.models.time_range import TimeRange
from groundshift.plugins.registry import PluginRegistry

REGION = BoundingBox(min_lon=35.0, min_lat=3.0, max_lon=42.0, max_lat=15.0)
BASE_TIME_RANGE = TimeRange(start=datetime(2040, 1, 1), end=datetime(2040, 12, 31))

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


def _make_runner(
    source: ClimateDataSource,
    scenarios: list[str] | None = None,
    horizons: list[int] | None = None,
):
    from groundshift.core.phases.predict import PredictPhaseRunner

    return PredictPhaseRunner(
        source,
        PluginRegistry(),
        scenarios=scenarios or ["ssp245"],
        horizons=horizons or [2040],
    )


class TestPredictPhaseRunner:
    def test_run_returns_predict_result(self):
        source = _ConstantSource({"mean_annual_temp_c": 21.0, "annual_precipitation_mm": 2000.0})
        runner = _make_runner(source)
        result = runner.run(_PROFILE, REGION, BASE_TIME_RANGE)
        assert isinstance(result, PredictResult)

    def test_run_produces_one_projection_per_scenario_horizon_combo(self):
        source = _ConstantSource({"mean_annual_temp_c": 21.0, "annual_precipitation_mm": 2000.0})
        runner = _make_runner(source, scenarios=["ssp245", "ssp585"], horizons=[2040, 2060])
        result = runner.run(_PROFILE, REGION, BASE_TIME_RANGE)
        assert len(result.projections) == 4

    def test_projections_are_predict_projection_instances(self):
        source = _ConstantSource({"mean_annual_temp_c": 21.0, "annual_precipitation_mm": 2000.0})
        runner = _make_runner(source)
        result = runner.run(_PROFILE, REGION, BASE_TIME_RANGE)
        assert all(isinstance(p, PredictProjection) for p in result.projections)

    def test_projection_scenario_is_set(self):
        source = _ConstantSource({"mean_annual_temp_c": 21.0, "annual_precipitation_mm": 2000.0})
        runner = _make_runner(source, scenarios=["ssp585"], horizons=[2060])
        result = runner.run(_PROFILE, REGION, BASE_TIME_RANGE)
        assert result.projections[0].scenario == "ssp585"

    def test_projection_horizon_year_is_set(self):
        source = _ConstantSource({"mean_annual_temp_c": 21.0, "annual_precipitation_mm": 2000.0})
        runner = _make_runner(source, scenarios=["ssp245"], horizons=[2100])
        result = runner.run(_PROFILE, REGION, BASE_TIME_RANGE)
        assert result.projections[0].horizon_year == 2100

    def test_projection_suitability_is_suitability_result(self):
        source = _ConstantSource({"mean_annual_temp_c": 21.0, "annual_precipitation_mm": 2000.0})
        runner = _make_runner(source)
        result = runner.run(_PROFILE, REGION, BASE_TIME_RANGE)
        assert isinstance(result.projections[0].suitability, SuitabilityResult)

    def test_projection_suitability_score_is_dataarray(self):
        source = _ConstantSource({"mean_annual_temp_c": 21.0, "annual_precipitation_mm": 2000.0})
        runner = _make_runner(source)
        result = runner.run(_PROFILE, REGION, BASE_TIME_RANGE)
        assert isinstance(result.projections[0].suitability.score, xr.DataArray)

    def test_optimal_climate_projects_score_one(self):
        import pytest

        source = _ConstantSource({"mean_annual_temp_c": 21.0, "annual_precipitation_mm": 2000.0})
        runner = _make_runner(source)
        result = runner.run(_PROFILE, REGION, BASE_TIME_RANGE)
        assert float(result.projections[0].suitability.score.mean()) == pytest.approx(1.0)

    def test_impossible_climate_projects_score_zero(self):
        import pytest

        source = _ConstantSource({"mean_annual_temp_c": 5.0, "annual_precipitation_mm": 2000.0})
        runner = _make_runner(source)
        result = runner.run(_PROFILE, REGION, BASE_TIME_RANGE)
        assert float(result.projections[0].suitability.score.mean()) == pytest.approx(0.0)

    def test_all_scenario_horizon_combos_covered(self):
        source = _ConstantSource({"mean_annual_temp_c": 21.0, "annual_precipitation_mm": 2000.0})
        runner = _make_runner(source, scenarios=["ssp245", "ssp585"], horizons=[2040, 2060, 2100])
        result = runner.run(_PROFILE, REGION, BASE_TIME_RANGE)
        combos = {(p.scenario, p.horizon_year) for p in result.projections}
        assert combos == {
            ("ssp245", 2040),
            ("ssp245", 2060),
            ("ssp245", 2100),
            ("ssp585", 2040),
            ("ssp585", 2060),
            ("ssp585", 2100),
        }
