"""
Unit tests for the pest disease ingest script pure functions.

The download itself is not tested here — it requires network access
and external data sources. Only the pure helper functions are covered.
"""

import numpy as np
import xarray as xr

from scripts.ingest.download_pest_disease import (
    _all_files_present,
    _clr_risk_from_climate,
    _expected_filenames,
)


def _scalar_da(value: float) -> xr.DataArray:
    return xr.DataArray(np.array([[value]], dtype="float32"))


class TestExpectedFilenames:
    def test_count_is_six(self):
        assert len(_expected_filenames()) == 6

    def test_contains_clr_filename(self):
        names = _expected_filenames()
        assert "pest_disease_clr_ssp245_2040.nc" in names

    def test_covers_both_scenarios(self):
        names = _expected_filenames()
        assert any("ssp245" in n for n in names)
        assert any("ssp585" in n for n in names)

    def test_covers_all_three_horizons(self):
        names = _expected_filenames()
        assert any("2040" in n for n in names)
        assert any("2060" in n for n in names)
        assert any("2100" in n for n in names)


class TestAllFilesPresent:
    def test_returns_true_when_all_exist(self, tmp_path):
        for name in _expected_filenames():
            (tmp_path / name).touch()
        assert _all_files_present(tmp_path) is True

    def test_returns_false_when_one_missing(self, tmp_path):
        for name in _expected_filenames()[:-1]:
            (tmp_path / name).touch()
        assert _all_files_present(tmp_path) is False

    def test_returns_false_for_empty_dir(self, tmp_path):
        assert _all_files_present(tmp_path) is False


class TestClrRiskFromClimate:
    def test_optimal_conditions_yield_high_risk(self):
        # 21°C, 1800mm — peak CLR conditions
        result = _clr_risk_from_climate(_scalar_da(21.0), _scalar_da(1800.0))
        assert float(result.mean()) > 0.7

    def test_cold_climate_yields_low_risk(self):
        # 5°C — below CLR viable range
        result = _clr_risk_from_climate(_scalar_da(5.0), _scalar_da(1500.0))
        assert float(result.mean()) < 0.2

    def test_hot_climate_yields_low_risk(self):
        # 36°C — above CLR viable range
        result = _clr_risk_from_climate(_scalar_da(36.0), _scalar_da(1500.0))
        assert float(result.mean()) < 0.2

    def test_dry_climate_lowers_risk(self):
        # Same temp, far less rainfall — moisture needed for sporulation
        wet = _clr_risk_from_climate(_scalar_da(20.0), _scalar_da(2000.0))
        dry = _clr_risk_from_climate(_scalar_da(20.0), _scalar_da(300.0))
        assert float(dry.mean()) < float(wet.mean())

    def test_output_in_unit_range(self):
        result = _clr_risk_from_climate(_scalar_da(21.0), _scalar_da(1800.0))
        assert 0.0 <= float(result.min()) <= float(result.max()) <= 1.0

    def test_returns_dataarray(self):
        result = _clr_risk_from_climate(_scalar_da(21.0), _scalar_da(1800.0))
        assert isinstance(result, xr.DataArray)
