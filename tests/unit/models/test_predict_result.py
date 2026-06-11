import numpy as np
import xarray as xr

from groundshift.models.predict_result import PredictProjection, PredictResult
from groundshift.models.suitability_result import SuitabilityResult


def _dummy_score() -> xr.DataArray:
    return xr.DataArray(np.array([[0.5, 0.8], [0.3, 0.6]]), dims=["y", "x"])


def _dummy_suitability() -> SuitabilityResult:
    score = _dummy_score()
    return SuitabilityResult(score=score, confidence=score)


class TestPredictProjection:
    def test_has_scenario_field(self):
        proj = PredictProjection(
            scenario="ssp245",
            horizon_year=2040,
            suitability=_dummy_suitability(),
        )
        assert proj.scenario == "ssp245"

    def test_has_horizon_year_field(self):
        proj = PredictProjection(
            scenario="ssp245",
            horizon_year=2040,
            suitability=_dummy_suitability(),
        )
        assert proj.horizon_year == 2040

    def test_has_suitability_field(self):
        suitability = _dummy_suitability()
        proj = PredictProjection(
            scenario="ssp245",
            horizon_year=2040,
            suitability=suitability,
        )
        assert proj.suitability is suitability


class TestPredictResult:
    def test_has_projections_field(self):
        proj = PredictProjection(
            scenario="ssp245",
            horizon_year=2040,
            suitability=_dummy_suitability(),
        )
        result = PredictResult(projections=[proj])
        assert len(result.projections) == 1

    def test_projections_are_predict_projections(self):
        proj = PredictProjection(
            scenario="ssp245",
            horizon_year=2040,
            suitability=_dummy_suitability(),
        )
        result = PredictResult(projections=[proj])
        assert isinstance(result.projections[0], PredictProjection)

    def test_accepts_multiple_projections(self):
        projections = [
            PredictProjection("ssp245", 2040, _dummy_suitability()),
            PredictProjection("ssp245", 2060, _dummy_suitability()),
            PredictProjection("ssp585", 2100, _dummy_suitability()),
        ]
        result = PredictResult(projections=projections)
        assert len(result.projections) == 3
