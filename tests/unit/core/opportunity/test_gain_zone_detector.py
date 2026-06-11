import numpy as np
import xarray as xr

from groundshift.core.opportunity.gain_zone_detector import GainZoneDetector
from groundshift.models.describe_result import DescribeResult
from groundshift.models.opportunity_zone import OpportunityZoneResult
from groundshift.models.prescribe_result import ChangeProjection, PrescribeResult
from groundshift.models.suitability_result import SuitabilityResult


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


class TestGainZoneDetector:
    def test_returns_opportunity_zone_result(self):
        detector = GainZoneDetector()
        result = detector.detect(_describe([[0.1]]), _prescribe([[0.5]]))
        assert isinstance(result, OpportunityZoneResult)

    def test_returns_one_zone_per_change_projection(self):
        prescribe = PrescribeResult(
            change_projections=[
                ChangeProjection("ssp245", 2040, xr.DataArray(np.array([[0.3]]))),
                ChangeProjection("ssp585", 2100, xr.DataArray(np.array([[0.4]]))),
            ]
        )
        result = GainZoneDetector().detect(_describe([[0.1]]), prescribe)
        assert len(result.zones) == 2

    def test_scenario_preserved_on_zone(self):
        result = GainZoneDetector().detect(_describe([[0.1]]), _prescribe([[0.5]]))
        assert result.zones[0].scenario == "ssp245"

    def test_horizon_year_preserved_on_zone(self):
        result = GainZoneDetector().detect(_describe([[0.1]]), _prescribe([[0.5]]))
        assert result.zones[0].horizon_year == 2040

    def test_mask_is_dataarray(self):
        result = GainZoneDetector().detect(_describe([[0.1]]), _prescribe([[0.5]]))
        assert isinstance(result.zones[0].mask, xr.DataArray)

    def test_cell_below_current_threshold_and_above_delta_threshold_is_true(self):
        # current=0.1 (below 0.3 default), delta=0.5 (above 0.1 default) → opportunity
        result = GainZoneDetector().detect(_describe([[0.1]]), _prescribe([[0.5]]))
        assert bool(result.zones[0].mask.values[0, 0]) is True

    def test_cell_already_viable_is_false(self):
        # current=0.9 (above threshold) → not emerging
        result = GainZoneDetector().detect(_describe([[0.9]]), _prescribe([[0.5]]))
        assert bool(result.zones[0].mask.values[0, 0]) is False

    def test_cell_with_insufficient_delta_is_false(self):
        # current=0.1 but delta=0.05 (below 0.1 default) → not enough gain
        result = GainZoneDetector().detect(_describe([[0.1]]), _prescribe([[0.05]]))
        assert bool(result.zones[0].mask.values[0, 0]) is False

    def test_cell_with_negative_delta_is_false(self):
        # current=0.1 but losing viability → not an opportunity
        result = GainZoneDetector().detect(_describe([[0.1]]), _prescribe([[-0.1]]))
        assert bool(result.zones[0].mask.values[0, 0]) is False

    def test_confidence_is_low_for_single_signal(self):
        result = GainZoneDetector().detect(_describe([[0.1]]), _prescribe([[0.5]]))
        assert result.zones[0].confidence == "low"

    def test_custom_current_threshold_respected(self):
        # current=0.5 — above default 0.3 but below custom 0.6 → should detect
        detector = GainZoneDetector(current_threshold=0.6)
        result = detector.detect(_describe([[0.5]]), _prescribe([[0.5]]))
        assert bool(result.zones[0].mask.values[0, 0]) is True

    def test_custom_delta_threshold_respected(self):
        # delta=0.05 — below default 0.1 but above custom 0.04 → should detect
        detector = GainZoneDetector(delta_threshold=0.04)
        result = detector.detect(_describe([[0.1]]), _prescribe([[0.05]]))
        assert bool(result.zones[0].mask.values[0, 0]) is True

    def test_spatial_mask_correct_across_multiple_cells(self):
        # 2x2 grid: only (0,0) qualifies
        current = [[0.1, 0.9], [0.1, 0.1]]
        delta = [[0.5, 0.5], [0.05, -0.2]]
        result = GainZoneDetector().detect(_describe(current), _prescribe(delta))
        mask = result.zones[0].mask.values
        assert mask[0, 0] is np.bool_(True)
        assert mask[0, 1] is np.bool_(False)  # current too high
        assert mask[1, 0] is np.bool_(False)  # delta too small
        assert mask[1, 1] is np.bool_(False)  # negative delta
