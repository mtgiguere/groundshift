"""
Tests for score_anchors.

Synthetic DataArrays use x (lon, ascending) and y (lat, descending) to
match the convention rioxarray produces when opening GeoTIFFs.
"""

import numpy as np
import pytest
import xarray as xr

from groundshift.core.calibration.anchor_scorer import score_anchors
from groundshift.models.anchor_score import AnchorScore
from groundshift.models.bounding_box import BoundingBox
from groundshift.models.calibration_anchor import CalibrationAnchor
from groundshift.models.suitability_result import SuitabilityResult

# 5×5 grid: lon 30–50 (step 5), lat 20→0 (step -5, descending like a raster)
_LONS = np.array([30.0, 35.0, 40.0, 45.0, 50.0])
_LATS = np.array([20.0, 15.0, 10.0, 5.0, 0.0])


def _make_result(score_fill: float = 0.8, conf_fill: float = 0.9) -> SuitabilityResult:
    data = np.full((5, 5), score_fill)
    conf = np.full((5, 5), conf_fill)
    score_da = xr.DataArray(data, dims=["y", "x"], coords={"y": _LATS, "x": _LONS})
    conf_da = xr.DataArray(conf, dims=["y", "x"], coords={"y": _LATS, "x": _LONS})
    return SuitabilityResult(score=score_da, confidence=conf_da)


def _anchor(
    role: str, min_lon: float, min_lat: float, max_lon: float, max_lat: float
) -> CalibrationAnchor:
    return CalibrationAnchor(
        anchor_id="test",
        name="Test",
        role=role,
        region=BoundingBox(min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat),
    )


def test_score_anchors_returns_one_result_per_anchor():
    anchors = [
        _anchor("origin_center", 33.0, 3.0, 42.0, 12.0),
        _anchor("production_reference", 33.0, 3.0, 42.0, 12.0),
    ]
    results = score_anchors(_make_result(), anchors)
    assert len(results) == 2


def test_score_anchors_returns_anchor_score_instances():
    anchors = [_anchor("origin_center", 33.0, 3.0, 42.0, 12.0)]
    results = score_anchors(_make_result(), anchors)
    assert isinstance(results[0], AnchorScore)


def test_score_anchors_returns_empty_list_for_no_anchors():
    assert score_anchors(_make_result(), []) == []


def test_score_anchors_mean_score_reflects_clipped_region():
    # Only the cell at (x=35, y=5) is in the anchor bbox.
    # Set that cell to 0.5; everything else to 0.9.
    data = np.full((5, 5), 0.9)
    # y=5 is index 3, x=35 is index 1
    data[3, 1] = 0.5
    score_da = xr.DataArray(data, dims=["y", "x"], coords={"y": _LATS, "x": _LONS})
    conf_da = xr.DataArray(np.ones((5, 5)), dims=["y", "x"], coords={"y": _LATS, "x": _LONS})
    result = SuitabilityResult(score=score_da, confidence=conf_da)

    anchor = _anchor("origin_center", 34.0, 4.0, 36.0, 6.0)  # clips to x=35, y=5 only
    scores = score_anchors(result, [anchor])
    assert scores[0].score == pytest.approx(0.5)


def test_score_anchors_origin_center_expected_min_is_0_70():
    anchors = [_anchor("origin_center", 33.0, 3.0, 42.0, 12.0)]
    results = score_anchors(_make_result(), anchors)
    assert results[0].expected_min == pytest.approx(0.70)


def test_score_anchors_production_reference_expected_min_is_0_60():
    anchors = [_anchor("production_reference", 33.0, 3.0, 42.0, 12.0)]
    results = score_anchors(_make_result(), anchors)
    assert results[0].expected_min == pytest.approx(0.60)


def test_score_anchors_stress_reference_expected_min_is_none():
    anchors = [_anchor("stress_reference", 33.0, 3.0, 42.0, 12.0)]
    results = score_anchors(_make_result(), anchors)
    assert results[0].expected_min is None


def test_score_anchors_origin_center_alert_triggers_below_threshold():
    # score_fill=0.5 < expected_min 0.70 → alert
    anchors = [_anchor("origin_center", 33.0, 3.0, 42.0, 12.0)]
    results = score_anchors(_make_result(score_fill=0.5), anchors)
    assert results[0].alert_triggered is True


def test_score_anchors_origin_center_no_alert_above_threshold():
    # score_fill=0.8 > expected_min 0.70 → no alert
    anchors = [_anchor("origin_center", 33.0, 3.0, 42.0, 12.0)]
    results = score_anchors(_make_result(score_fill=0.8), anchors)
    assert results[0].alert_triggered is False


def test_score_anchors_production_reference_alert_triggers_below_threshold():
    # score_fill=0.5 < expected_min 0.60 → alert
    anchors = [_anchor("production_reference", 33.0, 3.0, 42.0, 12.0)]
    results = score_anchors(_make_result(score_fill=0.5), anchors)
    assert results[0].alert_triggered is True


def test_score_anchors_stress_reference_never_triggers_alert():
    # stress_reference has no expected_min — never alerts regardless of score
    anchors = [_anchor("stress_reference", 33.0, 3.0, 42.0, 12.0)]
    results = score_anchors(_make_result(score_fill=0.95), anchors)
    assert results[0].alert_triggered is False


def test_score_anchors_no_alert_when_anchor_outside_result_extent():
    # Anchor bbox falls entirely outside the DataArray extent → mean is NaN.
    # NaN score must not trigger an alert (it's a data gap, not a bad score).
    anchor = _anchor("origin_center", 100.0, 80.0, 110.0, 85.0)
    results = score_anchors(_make_result(), [anchor])
    assert results[0].alert_triggered is False
