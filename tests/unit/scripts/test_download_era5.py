"""
Unit tests for the ERA5 ingest script pure functions.

The download itself (I/O boundary) is not tested here — it requires CDS API
credentials. Only the pure helper functions are covered.
"""
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from scripts.ingest.download_era5 import (
    _all_files_present,
    _expected_filenames,
    _geopotential_to_altitude,
    _kelvin_to_celsius,
    _precip_to_mm_per_year,
    _temp_cds_request,
)


def test_temp_cds_request_targets_correct_variable():
    req = _temp_cds_request(2015, 2024)
    assert req["variable"] == "2m_temperature"


def test_temp_cds_request_includes_all_months():
    req = _temp_cds_request(2015, 2024)
    assert req["month"] == [f"{m:02d}" for m in range(1, 13)]


def test_temp_cds_request_covers_requested_years():
    req = _temp_cds_request(2015, 2024)
    assert req["year"] == [str(y) for y in range(2015, 2025)]


def test_temp_cds_request_uses_monthly_averaged_reanalysis():
    req = _temp_cds_request(2015, 2024)
    assert req["product_type"] == "monthly_averaged_reanalysis"


def test_expected_filenames_contains_three_files():
    assert len(_expected_filenames()) == 3


def test_expected_filenames_match_era5_source_expectations():
    names = _expected_filenames()
    assert "era5_mean_annual_temp_c.nc" in names
    assert "era5_annual_precipitation_mm.nc" in names
    assert "era5_altitude_m.nc" in names


def test_all_files_present_returns_true_when_all_exist(tmp_path: Path):
    for name in _expected_filenames():
        (tmp_path / name).touch()
    assert _all_files_present(tmp_path) is True


def test_all_files_present_returns_false_when_one_missing(tmp_path: Path):
    names = _expected_filenames()
    for name in names[:-1]:  # write all but the last
        (tmp_path / name).touch()
    assert _all_files_present(tmp_path) is False


def _scalar_da(value: float) -> xr.DataArray:
    return xr.DataArray(np.array([[value]], dtype="float32"))


def test_kelvin_to_celsius_converts_correctly():
    result = _kelvin_to_celsius(_scalar_da(273.15))
    assert float(result.mean()) == pytest.approx(0.0, abs=1e-3)


def test_kelvin_to_celsius_typical_highland_temp():
    # 293.15 K = 20.0 °C
    result = _kelvin_to_celsius(_scalar_da(293.15))
    assert float(result.mean()) == pytest.approx(20.0, abs=1e-3)


def test_precip_to_mm_per_year_converts_correctly():
    # 1 m/day × 365.25 days/year × 1000 mm/m = 365250 mm/year
    result = _precip_to_mm_per_year(_scalar_da(1.0))
    assert float(result.mean()) == pytest.approx(365_250.0, abs=1.0)


def test_precip_to_mm_per_year_typical_highland_value():
    # ~4.11e-6 m/day → ~1500 mm/year (typical highland coffee zone)
    m_per_day = 1500.0 / (365.25 * 1000)
    result = _precip_to_mm_per_year(_scalar_da(m_per_day))
    assert float(result.mean()) == pytest.approx(1500.0, abs=1.0)


def test_geopotential_to_altitude_converts_correctly():
    # 9806.65 m²/s² / 9.80665 m/s² = 1000 m
    result = _geopotential_to_altitude(_scalar_da(9806.65))
    assert float(result.mean()) == pytest.approx(1000.0, abs=0.1)
