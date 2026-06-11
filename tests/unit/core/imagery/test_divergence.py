import numpy as np
import pytest
import xarray as xr

from groundshift.models.suitability_result import SuitabilityResult


def _make_result(score_val: float, confidence_val: float = 0.8) -> SuitabilityResult:
    coords = {"y": [10.0, 9.0, 8.0], "x": [35.0, 36.0, 37.0]}
    score = xr.DataArray(
        np.full((3, 3), score_val, dtype="float32"), dims=["y", "x"], coords=coords
    )
    confidence = xr.DataArray(
        np.full((3, 3), confidence_val, dtype="float32"), dims=["y", "x"], coords=coords
    )
    return SuitabilityResult(score=score, confidence=confidence)


def _make_ndvi(ndvi_val: float) -> xr.DataArray:
    coords = {"y": [10.0, 9.0, 8.0], "x": [35.0, 36.0, 37.0]}
    return xr.DataArray(np.full((3, 3), ndvi_val, dtype="float32"), dims=["y", "x"], coords=coords)


def test_divergence_result_has_surface_field():
    from groundshift.core.imagery.divergence import compute_divergence
    from groundshift.models.divergence_result import DivergenceResult

    result = compute_divergence(_make_result(0.8), _make_ndvi(0.6))
    assert isinstance(result, DivergenceResult)
    assert isinstance(result.surface, xr.DataArray)


def test_divergence_surface_values_are_in_minus_one_to_one():
    from groundshift.core.imagery.divergence import compute_divergence

    result = compute_divergence(_make_result(0.8), _make_ndvi(0.6))
    vals = result.surface.values[~np.isnan(result.surface.values)]
    assert float(vals.min()) >= -1.0
    assert float(vals.max()) <= 1.0


def test_positive_divergence_when_climate_exceeds_observed():
    # High climate score, low NDVI — climate says viable, satellite disagrees.
    # Normalized NDVI 0.2 → 0.6 (see normalization: (ndvi + 1) / 2).
    # divergence = climate_score − normalized_ndvi = 0.9 − 0.6 = 0.3
    from groundshift.core.imagery.divergence import compute_divergence

    result = compute_divergence(_make_result(0.9), _make_ndvi(0.2))
    val = float(result.surface.mean())
    assert val == pytest.approx(0.3, abs=1e-3)


def test_negative_divergence_when_observed_exceeds_climate():
    # Low climate score, high NDVI — satellite sees vegetation the model misses.
    # normalized_ndvi = (0.8 + 1) / 2 = 0.9
    # divergence = 0.3 − 0.9 = −0.6
    from groundshift.core.imagery.divergence import compute_divergence

    result = compute_divergence(_make_result(0.3), _make_ndvi(0.8))
    val = float(result.surface.mean())
    assert val == pytest.approx(-0.6, abs=1e-3)


def test_zero_divergence_when_climate_and_observed_agree():
    # climate_score = 0.75, ndvi = 0.5 → normalized = 0.75 → divergence = 0.0
    from groundshift.core.imagery.divergence import compute_divergence

    result = compute_divergence(_make_result(0.75), _make_ndvi(0.5))
    val = float(result.surface.mean())
    assert val == pytest.approx(0.0, abs=1e-3)


def test_divergence_result_preserves_spatial_coords():
    from groundshift.core.imagery.divergence import compute_divergence

    suitability = _make_result(0.7)
    result = compute_divergence(suitability, _make_ndvi(0.4))
    assert list(result.surface.dims) == ["y", "x"]
    assert float(result.surface.x.min()) == pytest.approx(35.0)
    assert float(result.surface.y.max()) == pytest.approx(10.0)


def test_divergence_propagates_nan_from_suitability():
    from groundshift.core.imagery.divergence import compute_divergence

    result_with_nan = _make_result(float("nan"))
    result = compute_divergence(result_with_nan, _make_ndvi(0.5))
    assert np.all(np.isnan(result.surface.values))
