import numpy as np
import xarray as xr

from groundshift.models.prescribe_result import ChangeProjection, PrescribeResult


def _delta() -> xr.DataArray:
    return xr.DataArray(np.array([[0.1, -0.2], [0.3, -0.1]]))


class TestChangeProjection:
    def test_has_scenario_field(self):
        proj = ChangeProjection(scenario="ssp245", horizon_year=2040, delta=_delta())
        assert proj.scenario == "ssp245"

    def test_has_horizon_year_field(self):
        proj = ChangeProjection(scenario="ssp245", horizon_year=2040, delta=_delta())
        assert proj.horizon_year == 2040

    def test_has_delta_field(self):
        d = _delta()
        proj = ChangeProjection(scenario="ssp245", horizon_year=2040, delta=d)
        assert proj.delta is d


class TestPrescribeResult:
    def test_has_change_projections_field(self):
        proj = ChangeProjection(scenario="ssp245", horizon_year=2040, delta=_delta())
        result = PrescribeResult(change_projections=[proj])
        assert len(result.change_projections) == 1

    def test_change_projections_are_change_projection_instances(self):
        proj = ChangeProjection(scenario="ssp245", horizon_year=2040, delta=_delta())
        result = PrescribeResult(change_projections=[proj])
        assert isinstance(result.change_projections[0], ChangeProjection)

    def test_accepts_multiple_projections(self):
        projections = [
            ChangeProjection("ssp245", 2040, _delta()),
            ChangeProjection("ssp245", 2060, _delta()),
            ChangeProjection("ssp585", 2100, _delta()),
        ]
        result = PrescribeResult(change_projections=projections)
        assert len(result.change_projections) == 3
