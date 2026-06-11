from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from scripts.ingest.download_sentinel2 import (
    _all_files_present,
    _expected_filenames,
    _ndvi_from_bands,
)


def _band(value: float) -> xr.DataArray:
    return xr.DataArray(np.full((4, 4), value, dtype="float32"))


def test_ndvi_formula_healthy_vegetation():
    # Typical healthy vegetation: NIR high, Red low → NDVI ≈ 0.6
    # (0.8 - 0.2) / (0.8 + 0.2) = 0.6
    result = _ndvi_from_bands(b4=_band(0.2), b8=_band(0.8))
    assert float(result.mean()) == pytest.approx(0.6, abs=1e-4)


def test_ndvi_is_one_when_pure_nir():
    # B4=0, B8=1 → (1-0)/(1+0) = 1.0
    result = _ndvi_from_bands(b4=_band(0.0), b8=_band(1.0))
    assert float(result.mean()) == pytest.approx(1.0, abs=1e-4)


def test_ndvi_is_minus_one_when_pure_red():
    # B4=1, B8=0 → (0-1)/(0+1) = -1.0
    result = _ndvi_from_bands(b4=_band(1.0), b8=_band(0.0))
    assert float(result.mean()) == pytest.approx(-1.0, abs=1e-4)


def test_ndvi_is_zero_when_bands_equal():
    # B4=B8 → (x-x)/(x+x) = 0
    result = _ndvi_from_bands(b4=_band(0.5), b8=_band(0.5))
    assert float(result.mean()) == pytest.approx(0.0, abs=1e-4)


def test_ndvi_output_is_dataarray():
    result = _ndvi_from_bands(b4=_band(0.2), b8=_band(0.8))
    assert isinstance(result, xr.DataArray)


def test_expected_filenames_matches_sentinel2_source():
    # Sentinel2Source looks for exactly these files — the download must
    # produce them. If Sentinel2Source._VARIABLE_MAP changes, this test
    # will catch the mismatch before a download run fails silently.
    assert _expected_filenames() == ["sentinel2_ndvi.tif"]


def test_all_files_present_returns_true_when_all_exist(tmp_path: Path):
    for name in _expected_filenames():
        (tmp_path / name).touch()
    assert _all_files_present(tmp_path)


def test_all_files_present_returns_false_when_missing(tmp_path: Path):
    assert not _all_files_present(tmp_path)
