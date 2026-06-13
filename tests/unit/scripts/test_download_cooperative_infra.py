"""
Unit tests for the cooperative infrastructure ingest script pure functions.

The download itself is not tested here — it requires OSM Overpass API access.
Only the pure helper functions are covered.
"""

import numpy as np
import pytest
import xarray as xr

from scripts.ingest.download_cooperative_infra import (
    _access_score_from_distance_km,
    _all_files_present,
    _expected_filename,
)


def _scalar_da(value: float) -> xr.DataArray:
    return xr.DataArray(np.array([[value]], dtype="float32"))


class TestExpectedFilename:
    def test_returns_single_string(self):
        assert isinstance(_expected_filename(), str)

    def test_contains_cooperative_infra(self):
        assert "cooperative_infra" in _expected_filename()

    def test_ends_with_nc(self):
        assert _expected_filename().endswith(".nc")


class TestAllFilesPresent:
    def test_returns_true_when_file_exists(self, tmp_path):
        (tmp_path / _expected_filename()).touch()
        assert _all_files_present(tmp_path) is True

    def test_returns_false_when_file_missing(self, tmp_path):
        assert _all_files_present(tmp_path) is False


class TestAccessScoreFromDistance:
    def test_zero_distance_gives_score_one(self):
        result = _access_score_from_distance_km(_scalar_da(0.0))
        assert float(result.mean()) == pytest.approx(1.0, abs=1e-3)

    def test_large_distance_gives_low_score(self):
        result = _access_score_from_distance_km(_scalar_da(500.0))
        assert float(result.mean()) < 0.1

    def test_closer_distance_gives_higher_score(self):
        near = _access_score_from_distance_km(_scalar_da(10.0))
        far = _access_score_from_distance_km(_scalar_da(100.0))
        assert float(near.mean()) > float(far.mean())

    def test_output_in_unit_range(self):
        for d in [0.0, 25.0, 100.0, 500.0]:
            result = _access_score_from_distance_km(_scalar_da(d))
            assert 0.0 <= float(result.min()) <= float(result.max()) <= 1.0

    def test_custom_decay_km_changes_curve(self):
        default = _access_score_from_distance_km(_scalar_da(50.0), decay_km=50.0)
        tighter = _access_score_from_distance_km(_scalar_da(50.0), decay_km=20.0)
        assert float(tighter.mean()) < float(default.mean())

    def test_returns_dataarray(self):
        result = _access_score_from_distance_km(_scalar_da(30.0))
        assert isinstance(result, xr.DataArray)
