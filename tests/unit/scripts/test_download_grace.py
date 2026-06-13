"""
Unit tests for the GRACE-FO TWS ingest script pure functions.

The download itself (I/O boundary) is not tested here — it requires
authentication to NASA GES DISC. Only the pure helper functions are covered.
"""

import numpy as np
import pytest
import xarray as xr

from scripts.ingest.download_grace import (
    _all_files_present,
    _expected_filename,
    _tws_to_cm,
)


def _scalar_da(value: float) -> xr.DataArray:
    return xr.DataArray(np.array([[value]], dtype="float32"))


class TestExpectedFilename:
    def test_returns_single_string(self):
        assert isinstance(_expected_filename(), str)

    def test_contains_groundwater(self):
        assert "groundwater" in _expected_filename()

    def test_ends_with_nc(self):
        assert _expected_filename().endswith(".nc")


class TestAllFilesPresent:
    def test_returns_true_when_file_exists(self, tmp_path):
        (tmp_path / _expected_filename()).touch()
        assert _all_files_present(tmp_path) is True

    def test_returns_false_when_file_missing(self, tmp_path):
        assert _all_files_present(tmp_path) is False


class TestTwsToCm:
    def test_cm_input_unchanged(self):
        result = _tws_to_cm(_scalar_da(-30.0), unit="cm")
        assert float(result.mean()) == pytest.approx(-30.0, abs=1e-3)

    def test_m_input_converted(self):
        result = _tws_to_cm(_scalar_da(-0.30), unit="m")
        assert float(result.mean()) == pytest.approx(-30.0, abs=1e-3)

    def test_zero_is_zero_in_both_units(self):
        assert float(_tws_to_cm(_scalar_da(0.0), unit="cm").mean()) == pytest.approx(0.0)
        assert float(_tws_to_cm(_scalar_da(0.0), unit="m").mean()) == pytest.approx(0.0)

    def test_positive_value_preserved(self):
        result = _tws_to_cm(_scalar_da(15.0), unit="cm")
        assert float(result.mean()) == pytest.approx(15.0, abs=1e-3)
