import xarray as xr

from groundshift.models.divergence_result import DivergenceResult
from groundshift.models.suitability_result import SuitabilityResult


def _normalize_ndvi(ndvi: xr.DataArray) -> xr.DataArray:
    # NDVI ∈ [−1, 1] → [0, 1] so it is directly comparable to suitability score.
    return (ndvi + 1.0) / 2.0


def compute_divergence(suitability: SuitabilityResult, ndvi: xr.DataArray) -> DivergenceResult:
    """Return the signed divergence between climate suitability and observed NDVI.

    Positive values: climate model predicts viability but satellite sees weak vegetation.
    Negative values: satellite sees strong vegetation the climate model underestimates.
    """
    normalized = _normalize_ndvi(ndvi)
    surface = suitability.score - normalized
    return DivergenceResult(surface=surface)
