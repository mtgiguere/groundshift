import numpy as np
import pytest
import xarray as xr

from groundshift.models.describe_result import DescribeResult
from groundshift.models.predict_result import PredictProjection, PredictResult
from groundshift.models.prescribe_result import ChangeProjection, PrescribeResult
from groundshift.models.suitability_result import SuitabilityResult


def _suitability(fill: float) -> SuitabilityResult:
    score = xr.DataArray(np.full((3, 3), fill))
    return SuitabilityResult(score=score, confidence=score)


def _describe(fill: float = 0.6) -> DescribeResult:
    return DescribeResult(suitability=_suitability(fill))


def _predict(*combos: tuple[str, int, float]) -> PredictResult:
    return PredictResult(
        projections=[
            PredictProjection(scenario=s, horizon_year=h, suitability=_suitability(v))
            for s, h, v in combos
        ]
    )


class TestPrescribePhaseRunner:
    def test_run_returns_prescribe_result(self):
        from groundshift.core.phases.prescribe import PrescribePhaseRunner

        result = PrescribePhaseRunner().run(_describe(), _predict(("ssp245", 2040, 0.7)))
        assert isinstance(result, PrescribeResult)

    def test_one_change_projection_per_predict_projection(self):
        from groundshift.core.phases.prescribe import PrescribePhaseRunner

        predict = _predict(("ssp245", 2040, 0.7), ("ssp585", 2060, 0.5), ("ssp585", 2100, 0.4))
        result = PrescribePhaseRunner().run(_describe(0.6), predict)
        assert len(result.change_projections) == 3

    def test_change_projections_are_correct_type(self):
        from groundshift.core.phases.prescribe import PrescribePhaseRunner

        result = PrescribePhaseRunner().run(_describe(), _predict(("ssp245", 2040, 0.7)))
        assert all(isinstance(p, ChangeProjection) for p in result.change_projections)

    def test_scenario_preserved_in_change_projection(self):
        from groundshift.core.phases.prescribe import PrescribePhaseRunner

        result = PrescribePhaseRunner().run(_describe(), _predict(("ssp585", 2060, 0.7)))
        assert result.change_projections[0].scenario == "ssp585"

    def test_horizon_year_preserved_in_change_projection(self):
        from groundshift.core.phases.prescribe import PrescribePhaseRunner

        result = PrescribePhaseRunner().run(_describe(), _predict(("ssp245", 2100, 0.7)))
        assert result.change_projections[0].horizon_year == 2100

    def test_delta_is_positive_when_projected_exceeds_current(self):
        from groundshift.core.phases.prescribe import PrescribePhaseRunner

        result = PrescribePhaseRunner().run(_describe(0.5), _predict(("ssp245", 2040, 0.8)))
        delta = result.change_projections[0].delta
        assert float(delta.mean()) == pytest.approx(0.3, abs=1e-5)

    def test_delta_is_negative_when_projected_below_current(self):
        from groundshift.core.phases.prescribe import PrescribePhaseRunner

        result = PrescribePhaseRunner().run(_describe(0.8), _predict(("ssp245", 2040, 0.5)))
        delta = result.change_projections[0].delta
        assert float(delta.mean()) == pytest.approx(-0.3, abs=1e-5)

    def test_delta_is_zero_when_projected_equals_current(self):
        from groundshift.core.phases.prescribe import PrescribePhaseRunner

        result = PrescribePhaseRunner().run(_describe(0.6), _predict(("ssp245", 2040, 0.6)))
        delta = result.change_projections[0].delta
        assert float(delta.mean()) == pytest.approx(0.0, abs=1e-5)

    def test_delta_is_dataarray(self):
        from groundshift.core.phases.prescribe import PrescribePhaseRunner

        result = PrescribePhaseRunner().run(_describe(), _predict(("ssp245", 2040, 0.7)))
        assert isinstance(result.change_projections[0].delta, xr.DataArray)

    def test_all_scenario_horizon_combos_in_output(self):
        from groundshift.core.phases.prescribe import PrescribePhaseRunner

        predict = _predict(
            ("ssp245", 2040, 0.7),
            ("ssp245", 2060, 0.65),
            ("ssp245", 2100, 0.55),
            ("ssp585", 2040, 0.68),
            ("ssp585", 2060, 0.58),
            ("ssp585", 2100, 0.40),
        )
        result = PrescribePhaseRunner().run(_describe(0.6), predict)
        combos = {(p.scenario, p.horizon_year) for p in result.change_projections}
        assert combos == {
            ("ssp245", 2040),
            ("ssp245", 2060),
            ("ssp245", 2100),
            ("ssp585", 2040),
            ("ssp585", 2060),
            ("ssp585", 2100),
        }
