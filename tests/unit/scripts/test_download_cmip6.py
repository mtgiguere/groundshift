"""
Unit tests for the CMIP6 ingest script pure functions.

The download itself (I/O boundary) is not tested here — it requires network
access to Google Cloud CMIP6 (Pangeo). Only the pure helper functions are covered.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from scripts.ingest.download_cmip6 import (
    _all_files_present,
    _annual_mean_from_monthly,
    _expected_filenames,
    _kelvin_to_celsius,
    _precip_flux_to_mm_year,
    _slice_horizon,
)


def _scalar_da(value: float) -> xr.DataArray:
    return xr.DataArray(np.array([[value]], dtype="float32"))


# ---------------------------------------------------------------------------
# _expected_filenames
# ---------------------------------------------------------------------------


def test_expected_filenames_count_is_twelve():
    # 2 variables × 2 scenarios × 3 horizons = 12
    assert len(_expected_filenames()) == 12


def test_expected_filenames_match_cmip6source_convention():
    names = _expected_filenames()
    assert "cmip6_mean_annual_temp_c_ssp245_2040.nc" in names
    assert "cmip6_annual_precipitation_mm_ssp585_2100.nc" in names


def test_expected_filenames_covers_both_scenarios():
    names = _expected_filenames()
    ssp245 = [n for n in names if "ssp245" in n]
    ssp585 = [n for n in names if "ssp585" in n]
    assert len(ssp245) == 6  # 2 variables × 3 horizons
    assert len(ssp585) == 6


def test_expected_filenames_covers_all_three_horizons():
    names = _expected_filenames()
    assert any("2040" in n for n in names)
    assert any("2060" in n for n in names)
    assert any("2100" in n for n in names)


# ---------------------------------------------------------------------------
# _all_files_present
# ---------------------------------------------------------------------------


def test_all_files_present_returns_true_when_all_exist(tmp_path: Path):
    for name in _expected_filenames():
        (tmp_path / name).touch()
    assert _all_files_present(tmp_path) is True


def test_all_files_present_returns_false_when_one_missing(tmp_path: Path):
    names = _expected_filenames()
    for name in names[:-1]:
        (tmp_path / name).touch()
    assert _all_files_present(tmp_path) is False


# ---------------------------------------------------------------------------
# _kelvin_to_celsius
# ---------------------------------------------------------------------------


def test_kelvin_to_celsius_freezing_point():
    result = _kelvin_to_celsius(_scalar_da(273.15))
    assert float(result.mean()) == pytest.approx(0.0, abs=1e-3)


def test_kelvin_to_celsius_typical_highland_temp():
    # 294.15 K = 21.0 °C — inside the Arabica optimal range
    result = _kelvin_to_celsius(_scalar_da(294.15))
    assert float(result.mean()) == pytest.approx(21.0, abs=1e-3)


# ---------------------------------------------------------------------------
# _precip_flux_to_mm_year
# ---------------------------------------------------------------------------


def test_precip_flux_to_mm_year_unit_flux():
    # 1 kg m⁻² s⁻¹ × 86400 s/day × 365.25 days/year = 31_557_600 mm/year
    result = _precip_flux_to_mm_year(_scalar_da(1.0))
    assert float(result.mean()) == pytest.approx(31_557_600.0, rel=1e-4)


def test_precip_flux_to_mm_year_typical_highland_value():
    # ~4.756e-5 kg m⁻² s⁻¹ → ~1500 mm/year (typical Arabica highland)
    flux = 1500.0 / (86400.0 * 365.25)
    result = _precip_flux_to_mm_year(_scalar_da(flux))
    assert float(result.mean()) == pytest.approx(1500.0, rel=1e-3)


# ---------------------------------------------------------------------------
# _annual_mean_from_monthly
# ---------------------------------------------------------------------------


def _monthly_da(year_start: int, n_years: int, fill_value: float = 1.0) -> xr.DataArray:
    times = pd.date_range(f"{year_start}-01", periods=n_years * 12, freq="MS")
    data = np.full((len(times), 2, 2), fill_value, dtype="float32")
    return xr.DataArray(data, dims=["time", "y", "x"], coords={"time": times})


def test_annual_mean_from_monthly_returns_one_value_per_year():
    da = _monthly_da(2035, n_years=3)
    result = _annual_mean_from_monthly(da)
    assert result.sizes["year"] == 3


def test_annual_mean_from_monthly_constant_input_unchanged():
    da = _monthly_da(2035, n_years=2, fill_value=21.0)
    result = _annual_mean_from_monthly(da)
    assert float(result.mean()) == pytest.approx(21.0, abs=1e-3)


def test_annual_mean_from_monthly_averages_within_year():
    times = pd.date_range("2035-01", periods=12, freq="MS")
    # Jan-Jun = 0.0, Jul-Dec = 12.0  →  annual mean = 6.0
    values = np.array([0.0] * 6 + [12.0] * 6, dtype="float32")
    da = xr.DataArray(values, dims=["time"], coords={"time": times})
    result = _annual_mean_from_monthly(da)
    assert float(result.mean()) == pytest.approx(6.0, abs=1e-3)


# ---------------------------------------------------------------------------
# _slice_horizon
# ---------------------------------------------------------------------------


def _annual_da(year_start: int, year_end: int) -> xr.DataArray:
    years = np.arange(year_start, year_end + 1)
    # Each cell value equals the year — makes it easy to check window means
    data = np.broadcast_to(years[:, None, None], (len(years), 2, 2)).astype("float32").copy()
    return xr.DataArray(data, dims=["year", "y", "x"], coords={"year": years})


def test_slice_horizon_mean_equals_centre_year_for_symmetric_range():
    # Window 2035–2045 around 2040 — mean of [2035..2045] = 2040.0
    da = _annual_da(2030, 2055)
    result = _slice_horizon(da, horizon_year=2040, half_width=5)
    assert float(result.mean()) == pytest.approx(2040.0, abs=1e-2)


def test_slice_horizon_respects_half_width():
    da = _annual_da(2030, 2070)
    # half_width=2 → window [2038, 2042] around 2040 → mean = 2040.0
    result = _slice_horizon(da, horizon_year=2040, half_width=2)
    assert float(result.mean()) == pytest.approx(2040.0, abs=1e-2)


def test_slice_horizon_returns_spatial_dataarray():
    da = _annual_da(2030, 2055)
    result = _slice_horizon(da, horizon_year=2040, half_width=5)
    assert isinstance(result, xr.DataArray)
    assert "year" not in result.dims
