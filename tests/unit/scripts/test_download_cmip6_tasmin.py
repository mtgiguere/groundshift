"""
Unit tests for the CMIP6 tasmin ingest script pure functions.

The download itself (I/O boundary) is not tested here — it requires network
access to Google Cloud CMIP6 (Pangeo). Only the pure helper functions are covered.
"""

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from scripts.ingest.download_cmip6_tasmin import (
    _all_files_present,
    _annual_min_from_monthly,
    _expected_filenames,
    _slice_horizon,
    _tasmin_to_celsius,
)


def _scalar_da(value: float) -> xr.DataArray:
    return xr.DataArray(np.array([[value]], dtype="float32"))


class TestExpectedFilenames:
    def test_count_is_six(self):
        # 1 variable × 2 scenarios × 3 horizons = 6
        assert len(_expected_filenames()) == 6

    def test_contains_frost_risk_filename(self):
        names = _expected_filenames()
        assert "frost_risk_min_temp_ssp245_2040.nc" in names

    def test_covers_both_scenarios(self):
        names = _expected_filenames()
        assert any("ssp245" in n for n in names)
        assert any("ssp585" in n for n in names)

    def test_covers_all_three_horizons(self):
        names = _expected_filenames()
        assert any("2040" in n for n in names)
        assert any("2060" in n for n in names)
        assert any("2100" in n for n in names)

    def test_custom_scenarios_and_horizons(self):
        names = _expected_filenames(["ssp245"], [2040])
        assert names == ["frost_risk_min_temp_ssp245_2040.nc"]


class TestAllFilesPresent:
    def test_returns_true_when_all_exist(self, tmp_path):
        for name in _expected_filenames():
            (tmp_path / name).touch()
        assert _all_files_present(tmp_path) is True

    def test_returns_false_when_one_missing(self, tmp_path):
        names = _expected_filenames()
        for name in names[:-1]:
            (tmp_path / name).touch()
        assert _all_files_present(tmp_path) is False

    def test_returns_false_for_empty_dir(self, tmp_path):
        assert _all_files_present(tmp_path) is False


class TestTasminToCelsius:
    def test_freezing_point(self):
        result = _tasmin_to_celsius(_scalar_da(273.15))
        assert float(result.mean()) == pytest.approx(0.0, abs=1e-3)

    def test_typical_cold_night(self):
        # 268.15 K = −5.0 °C
        result = _tasmin_to_celsius(_scalar_da(268.15))
        assert float(result.mean()) == pytest.approx(-5.0, abs=1e-3)

    def test_boiling_point(self):
        result = _tasmin_to_celsius(_scalar_da(373.15))
        assert float(result.mean()) == pytest.approx(100.0, abs=1e-3)


class TestAnnualMinFromMonthly:
    def _monthly_da(self, year_start: int, n_years: int, fill_value: float = 1.0):
        times = pd.date_range(f"{year_start}-01", periods=n_years * 12, freq="MS")
        data = np.full((len(times), 2, 2), fill_value, dtype="float32")
        return xr.DataArray(data, dims=["time", "y", "x"], coords={"time": times})

    def test_returns_one_value_per_year(self):
        da = self._monthly_da(2035, n_years=3)
        result = _annual_min_from_monthly(da)
        assert result.sizes["year"] == 3

    def test_constant_input_unchanged(self):
        da = self._monthly_da(2035, n_years=2, fill_value=-5.0)
        result = _annual_min_from_monthly(da)
        assert float(result.mean()) == pytest.approx(-5.0, abs=1e-3)

    def test_returns_minimum_not_mean(self):
        times = pd.date_range("2035-01", periods=12, freq="MS")
        # Jan = −10.0, all other months = 5.0 → min = −10.0, mean = 3.75
        values = np.array([-10.0] + [5.0] * 11, dtype="float32")
        da = xr.DataArray(values, dims=["time"], coords={"time": times})
        result = _annual_min_from_monthly(da)
        assert float(result.values.flat[0]) == pytest.approx(-10.0, abs=1e-3)

    def test_drops_time_dimension(self):
        da = self._monthly_da(2035, n_years=2)
        result = _annual_min_from_monthly(da)
        assert "time" not in result.dims
        assert "year" in result.dims


class TestSliceHorizon:
    def _annual_da(self, year_start: int, year_end: int) -> xr.DataArray:
        years = np.arange(year_start, year_end + 1)
        data = np.broadcast_to(years[:, None, None], (len(years), 2, 2)).astype("float32").copy()
        return xr.DataArray(data, dims=["year", "y", "x"], coords={"year": years})

    def test_mean_equals_centre_year(self):
        da = self._annual_da(2030, 2055)
        result = _slice_horizon(da, horizon_year=2040, half_width=5)
        assert float(result.mean()) == pytest.approx(2040.0, abs=1e-2)

    def test_respects_half_width(self):
        da = self._annual_da(2030, 2070)
        result = _slice_horizon(da, horizon_year=2040, half_width=2)
        assert float(result.mean()) == pytest.approx(2040.0, abs=1e-2)

    def test_returns_spatial_dataarray(self):
        da = self._annual_da(2030, 2055)
        result = _slice_horizon(da, horizon_year=2040, half_width=5)
        assert isinstance(result, xr.DataArray)
        assert "year" not in result.dims
