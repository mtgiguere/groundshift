import numpy as np
import pytest
import xarray as xr

from scripts.ingest.download_landsat import (
    _all_files_present,
    _annual_median,
    _compute_ndvi,
    _compute_trend,
    _expected_filename,
)


def _da(values) -> xr.DataArray:
    return xr.DataArray(np.array(values, dtype=float))


class TestExpectedFilename:
    def test_returns_string(self):
        assert isinstance(_expected_filename("ethiopia"), str)

    def test_contains_region(self):
        assert "ethiopia" in _expected_filename("ethiopia")

    def test_is_tif(self):
        assert _expected_filename("ethiopia").endswith(".tif")

    def test_differs_by_region(self):
        assert _expected_filename("ethiopia") != _expected_filename("colombia")


class TestAllFilesPresent:
    def test_returns_false_when_dir_empty(self, tmp_path):
        assert _all_files_present(tmp_path, "ethiopia") is False

    def test_returns_true_when_file_exists(self, tmp_path):
        (tmp_path / _expected_filename("ethiopia")).touch()
        assert _all_files_present(tmp_path, "ethiopia") is True


class TestComputeNdvi:
    def test_returns_dataarray(self):
        red = _da([[0.1, 0.2]])
        nir = _da([[0.4, 0.5]])
        result = _compute_ndvi(red, nir)
        assert isinstance(result, xr.DataArray)

    def test_formula_is_correct(self):
        # NDVI = (NIR - Red) / (NIR + Red)
        red = _da([[0.1]])
        nir = _da([[0.3]])
        result = _compute_ndvi(red, nir)
        expected = (0.3 - 0.1) / (0.3 + 0.1)
        assert float(result.values[0, 0]) == pytest.approx(expected)

    def test_values_in_range(self):
        red = _da([[0.05, 0.2], [0.15, 0.3]])
        nir = _da([[0.35, 0.1], [0.45, 0.25]])
        result = _compute_ndvi(red, nir)
        assert float(result.min()) >= -1.0
        assert float(result.max()) <= 1.0


class TestAnnualMedian:
    def test_returns_dataarray(self):
        time = xr.DataArray(np.array([2010, 2010, 2011], dtype=int), dims=["time"])
        ndvi = xr.DataArray(
            np.array([[[0.4]], [[0.5]], [[0.3]]]),
            dims=["time", "y", "x"],
            coords={"time": time},
        )
        result = _annual_median(ndvi)
        assert isinstance(result, xr.DataArray)

    def test_reduces_to_annual_values(self):
        time = xr.DataArray(np.array([2010, 2010, 2011], dtype=int), dims=["time"])
        ndvi = xr.DataArray(
            np.array([[[0.4]], [[0.6]], [[0.3]]]),
            dims=["time", "y", "x"],
            coords={"time": time},
        )
        result = _annual_median(ndvi)
        # 2010 median of [0.4, 0.6] = 0.5; 2011 = 0.3
        assert result.sizes["time"] == 2

    def test_median_is_correct(self):
        time = xr.DataArray(np.array([2010, 2010], dtype=int), dims=["time"])
        ndvi = xr.DataArray(
            np.array([[[0.4]], [[0.6]]]),
            dims=["time", "y", "x"],
            coords={"time": time},
        )
        result = _annual_median(ndvi)
        assert float(result.isel(time=0).values[0, 0]) == pytest.approx(0.5)


class TestComputeTrend:
    def test_returns_dataarray(self):
        years = np.array([2010, 2011, 2012, 2013, 2014])
        data = np.stack([np.full((2, 2), 0.4 + i * 0.01) for i in range(5)])
        ndvi = xr.DataArray(data, dims=["time", "y", "x"], coords={"time": years})
        result = _compute_trend(ndvi)
        assert isinstance(result, xr.DataArray)

    def test_positive_trend_for_increasing_ndvi(self):
        years = np.array([2010, 2011, 2012, 2013, 2014])
        data = np.stack([np.full((1, 1), 0.4 + i * 0.01) for i in range(5)])
        ndvi = xr.DataArray(data, dims=["time", "y", "x"], coords={"time": years})
        slope = _compute_trend(ndvi)
        assert float(slope.values[0, 0]) > 0

    def test_negative_trend_for_declining_ndvi(self):
        years = np.array([2010, 2011, 2012, 2013, 2014])
        data = np.stack([np.full((1, 1), 0.6 - i * 0.01) for i in range(5)])
        ndvi = xr.DataArray(data, dims=["time", "y", "x"], coords={"time": years})
        slope = _compute_trend(ndvi)
        assert float(slope.values[0, 0]) < 0

    def test_slope_magnitude_is_correct(self):
        # Perfect linear increase of 0.01 NDVI/year
        years = np.array([2010, 2011, 2012, 2013, 2014])
        data = np.stack([np.full((1, 1), 0.4 + i * 0.01) for i in range(5)])
        ndvi = xr.DataArray(data, dims=["time", "y", "x"], coords={"time": years})
        slope = _compute_trend(ndvi)
        assert float(slope.values[0, 0]) == pytest.approx(0.01, abs=1e-6)
