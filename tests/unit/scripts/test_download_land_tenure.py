"""Unit tests for download_land_tenure pure helper functions."""

import numpy as np
import pytest
import xarray as xr

from scripts.ingest.download_land_tenure import (
    _all_files_present,
    _expected_filename,
    _security_score_from_prindex,
)


class TestExpectedFilename:
    def test_returns_correct_name(self):
        assert _expected_filename() == "land_tenure_security.nc"

    def test_ends_with_nc(self):
        assert _expected_filename().endswith(".nc")


class TestAllFilesPresent:
    def test_false_when_dir_empty(self, tmp_path):
        assert _all_files_present(tmp_path) is False

    def test_true_when_file_exists(self, tmp_path):
        (tmp_path / "land_tenure_security.nc").touch()
        assert _all_files_present(tmp_path) is True

    def test_false_when_different_file_present(self, tmp_path):
        (tmp_path / "other_file.nc").touch()
        assert _all_files_present(tmp_path) is False


class TestSecurityScoreFromPrindex:
    def test_prindex_100_gives_one(self):
        da = xr.DataArray(np.array([[100.0]]))
        result = _security_score_from_prindex(da)
        assert float(result.values.flat[0]) == pytest.approx(1.0, abs=1e-6)

    def test_prindex_0_gives_zero(self):
        da = xr.DataArray(np.array([[0.0]]))
        result = _security_score_from_prindex(da)
        assert float(result.values.flat[0]) == pytest.approx(0.0, abs=1e-6)

    def test_prindex_50_gives_point_5(self):
        da = xr.DataArray(np.array([[50.0]]))
        result = _security_score_from_prindex(da)
        assert float(result.values.flat[0]) == pytest.approx(0.5, abs=1e-6)

    def test_prindex_above_100_clipped_to_one(self):
        da = xr.DataArray(np.array([[120.0]]))
        result = _security_score_from_prindex(da)
        assert float(result.values.flat[0]) == pytest.approx(1.0, abs=1e-6)

    def test_prindex_negative_clipped_to_zero(self):
        da = xr.DataArray(np.array([[-10.0]]))
        result = _security_score_from_prindex(da)
        assert float(result.values.flat[0]) == pytest.approx(0.0, abs=1e-6)

    def test_preserves_shape(self):
        da = xr.DataArray(np.full((3, 4), 75.0, dtype="float32"))
        result = _security_score_from_prindex(da)
        assert result.shape == (3, 4)
