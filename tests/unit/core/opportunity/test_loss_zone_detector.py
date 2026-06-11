import numpy as np
import xarray as xr

from groundshift.core.opportunity.loss_zone_detector import LossZoneDetector
from groundshift.models.describe_result import DescribeResult
from groundshift.models.divergence_result import DivergenceResult
from groundshift.models.loss_zone import LossZoneResult
from groundshift.models.prescribe_result import ChangeProjection, PrescribeResult
from groundshift.models.suitability_result import SuitabilityResult
from groundshift.models.trend_result import TrendResult


def _describe(current_scores) -> DescribeResult:
    score = xr.DataArray(np.array(current_scores, dtype=float))
    return DescribeResult(suitability=SuitabilityResult(score=score, confidence=score))


def _prescribe(deltas) -> PrescribeResult:
    return PrescribeResult(
        change_projections=[
            ChangeProjection(
                scenario="ssp245",
                horizon_year=2040,
                delta=xr.DataArray(np.array(deltas, dtype=float)),
            )
        ]
    )


class TestLossZoneDetector:
    def test_returns_loss_zone_result(self):
        detector = LossZoneDetector()
        result = detector.detect(_describe([[0.8]]), _prescribe([[-0.5]]))
        assert isinstance(result, LossZoneResult)

    def test_returns_one_zone_per_change_projection(self):
        prescribe = PrescribeResult(
            change_projections=[
                ChangeProjection("ssp245", 2040, xr.DataArray(np.array([[-0.3]]))),
                ChangeProjection("ssp585", 2100, xr.DataArray(np.array([[-0.4]]))),
            ]
        )
        result = LossZoneDetector().detect(_describe([[0.8]]), prescribe)
        assert len(result.zones) == 2

    def test_scenario_preserved_on_zone(self):
        result = LossZoneDetector().detect(_describe([[0.8]]), _prescribe([[-0.5]]))
        assert result.zones[0].scenario == "ssp245"

    def test_horizon_year_preserved_on_zone(self):
        result = LossZoneDetector().detect(_describe([[0.8]]), _prescribe([[-0.5]]))
        assert result.zones[0].horizon_year == 2040

    def test_mask_is_dataarray(self):
        result = LossZoneDetector().detect(_describe([[0.8]]), _prescribe([[-0.5]]))
        assert isinstance(result.zones[0].mask, xr.DataArray)

    def test_cell_above_current_threshold_and_below_delta_threshold_is_true(self):
        # current=0.8 (above 0.3 default), delta=-0.5 (below -0.1 default) → loss zone
        result = LossZoneDetector().detect(_describe([[0.8]]), _prescribe([[-0.5]]))
        assert bool(result.zones[0].mask.values[0, 0]) is True

    def test_cell_already_low_suitability_is_false(self):
        # current=0.1 (below threshold) → not a loss zone
        result = LossZoneDetector().detect(_describe([[0.1]]), _prescribe([[-0.5]]))
        assert bool(result.zones[0].mask.values[0, 0]) is False

    def test_cell_with_insufficient_negative_delta_is_false(self):
        # current=0.8 but delta=-0.05 (above -0.1 default) → not enough loss
        result = LossZoneDetector().detect(_describe([[0.8]]), _prescribe([[-0.05]]))
        assert bool(result.zones[0].mask.values[0, 0]) is False

    def test_cell_with_positive_delta_is_false(self):
        # current=0.8 but gaining viability → not a loss zone
        result = LossZoneDetector().detect(_describe([[0.8]]), _prescribe([[0.2]]))
        assert bool(result.zones[0].mask.values[0, 0]) is False

    def test_confidence_is_low_for_single_signal(self):
        result = LossZoneDetector().detect(_describe([[0.8]]), _prescribe([[-0.5]]))
        assert result.zones[0].confidence == "low"

    def test_confidence_is_medium_with_supporting_landsat(self):
        d = _describe([[0.8]])
        d.trend = TrendResult(slope=xr.DataArray(np.array([[-0.003]])))  # negative → loss
        result = LossZoneDetector().detect(d, _prescribe([[-0.5]]))
        assert result.zones[0].confidence == "medium"

    def test_confidence_is_medium_with_supporting_sentinel2(self):
        d = _describe([[0.8]])
        d.divergence = DivergenceResult(surface=xr.DataArray(np.array([[0.2]])))  # positive → loss
        result = LossZoneDetector().detect(d, _prescribe([[-0.5]]))
        assert result.zones[0].confidence == "medium"

    def test_confidence_is_high_with_both_supporting(self):
        d = _describe([[0.8]])
        d.trend = TrendResult(slope=xr.DataArray(np.array([[-0.003]])))
        d.divergence = DivergenceResult(surface=xr.DataArray(np.array([[0.2]])))
        result = LossZoneDetector().detect(d, _prescribe([[-0.5]]))
        assert result.zones[0].confidence == "high"

    def test_confidence_stays_low_when_landsat_contradicts(self):
        d = _describe([[0.8]])
        d.trend = TrendResult(slope=xr.DataArray(np.array([[0.003]])))  # positive → contradicts
        result = LossZoneDetector().detect(d, _prescribe([[-0.5]]))
        assert result.zones[0].confidence == "low"

    def test_confidence_stays_low_when_sentinel2_contradicts(self):
        d = _describe([[0.8]])
        d.divergence = DivergenceResult(surface=xr.DataArray(np.array([[-0.2]])))
        result = LossZoneDetector().detect(d, _prescribe([[-0.5]]))
        assert result.zones[0].confidence == "low"

    def test_confidence_medium_when_one_supports_one_contradicts(self):
        d = _describe([[0.8]])
        d.trend = TrendResult(slope=xr.DataArray(np.array([[-0.003]])))  # supports
        d.divergence = DivergenceResult(surface=xr.DataArray(np.array([[-0.2]])))  # contradicts
        result = LossZoneDetector().detect(d, _prescribe([[-0.5]]))
        assert result.zones[0].confidence == "medium"

    def test_custom_current_threshold_respected(self):
        # current=0.2 — below default 0.3 but above custom 0.15 → should detect
        detector = LossZoneDetector(current_threshold=0.15)
        result = detector.detect(_describe([[0.2]]), _prescribe([[-0.5]]))
        assert bool(result.zones[0].mask.values[0, 0]) is True

    def test_custom_delta_threshold_respected(self):
        # delta=-0.05 — above default -0.1 but below custom -0.04 → should detect
        detector = LossZoneDetector(delta_threshold=0.04)
        result = detector.detect(_describe([[0.8]]), _prescribe([[-0.05]]))
        assert bool(result.zones[0].mask.values[0, 0]) is True

    def test_spatial_mask_correct_across_multiple_cells(self):
        # 2x2 grid: only (0,0) qualifies as a loss zone
        current = [[0.8, 0.1], [0.8, 0.8]]
        delta = [[-0.5, -0.5], [-0.05, 0.2]]
        result = LossZoneDetector().detect(_describe(current), _prescribe(delta))
        mask = result.zones[0].mask.values
        assert mask[0, 0] is np.bool_(True)
        assert mask[0, 1] is np.bool_(False)  # current too low
        assert mask[1, 0] is np.bool_(False)  # delta not severe enough
        assert mask[1, 1] is np.bool_(False)  # positive delta
