"""Unit tests for download_phenology pure helper functions."""

import numpy as np
import pytest
import xarray as xr

from scripts.ingest.download_phenology import (
    _all_files_present,
    _expected_filenames,
    _gdd_from_mean_temp,
)


class TestExpectedFilenames:
    def test_returns_six_files(self):
        assert len(_expected_filenames()) == 6

    def test_covers_both_scenarios(self):
        names = _expected_filenames()
        assert any("ssp245" in n for n in names)
        assert any("ssp585" in n for n in names)

    def test_covers_three_horizons(self):
        names = _expected_filenames()
        assert any("2040" in n for n in names)
        assert any("2060" in n for n in names)
        assert any("2080" in n for n in names)

    def test_filenames_start_with_phenology_gdd(self):
        for name in _expected_filenames():
            assert name.startswith("phenology_gdd_")

    def test_filenames_end_with_nc(self):
        for name in _expected_filenames():
            assert name.endswith(".nc")


class TestAllFilesPresent:
    def test_false_when_dir_empty(self, tmp_path):
        assert _all_files_present(tmp_path) is False

    def test_false_when_only_some_files_present(self, tmp_path):
        (tmp_path / "phenology_gdd_ssp245_2040.nc").touch()
        assert _all_files_present(tmp_path) is False

    def test_true_when_all_six_files_present(self, tmp_path):
        for name in _expected_filenames():
            (tmp_path / name).touch()
        assert _all_files_present(tmp_path) is True


class TestGddFromMeanTemp:
    def test_positive_temp_multiplied_by_365(self):
        da = xr.DataArray(np.array([[20.0]]))
        result = _gdd_from_mean_temp(da)
        assert float(result.values.flat[0]) == pytest.approx(20.0 * 365.0, abs=1e-3)

    def test_negative_temp_gives_zero(self):
        da = xr.DataArray(np.array([[-5.0]]))
        result = _gdd_from_mean_temp(da)
        assert float(result.values.flat[0]) == pytest.approx(0.0, abs=1e-6)

    def test_zero_temp_gives_zero(self):
        da = xr.DataArray(np.array([[0.0]]))
        result = _gdd_from_mean_temp(da)
        assert float(result.values.flat[0]) == pytest.approx(0.0, abs=1e-6)

    def test_result_has_no_negative_values(self):
        da = xr.DataArray(np.array([[-10.0, 5.0, 20.0]]))
        result = _gdd_from_mean_temp(da)
        assert float(result.min()) >= 0.0

    def test_preserves_shape(self):
        da = xr.DataArray(np.ones((3, 4), dtype="float32") * 15.0)
        result = _gdd_from_mean_temp(da)
        assert result.shape == (3, 4)
