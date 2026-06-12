from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from scripts.prepare_plugin_data import (
    _plugin_filenames,
    prepare_all_plugin_data,
    prepare_drought_stress_data,
    prepare_heat_stress_data,
)


def _write_cmip6_nc(data_dir: Path, variable: str, scenario: str, horizon: int) -> Path:
    path = data_dir / f"cmip6_{variable}_{scenario}_{horizon}.nc"
    lats = np.linspace(10, 0, 4)
    lons = np.linspace(30, 40, 4)
    da = xr.DataArray(
        np.random.default_rng(0).random((4, 4)),
        coords={"lat": lats, "lon": lons},
        dims=["lat", "lon"],
    )
    da.to_dataset(name=variable).to_netcdf(path)
    return path


@pytest.fixture
def cmip6_dir(tmp_path):
    src = tmp_path / "cmip6"
    src.mkdir()
    _write_cmip6_nc(src, "annual_precipitation_mm", "ssp245", 2040)
    _write_cmip6_nc(src, "annual_precipitation_mm", "ssp585", 2060)
    _write_cmip6_nc(src, "mean_annual_temp_c", "ssp245", 2040)
    _write_cmip6_nc(src, "mean_annual_temp_c", "ssp585", 2060)
    return src


@pytest.fixture
def out_dir(tmp_path):
    return tmp_path / "plugin_data"


class TestPluginFilenames:
    def test_returns_list(self):
        result = _plugin_filenames(["ssp245"], [2040])
        assert isinstance(result, list)

    def test_contains_drought_stress_filename(self):
        names = _plugin_filenames(["ssp245"], [2040])
        assert "drought_stress_precip_ssp245_2040.nc" in names

    def test_contains_heat_stress_filename(self):
        names = _plugin_filenames(["ssp245"], [2040])
        assert "heat_stress_mean_temp_ssp245_2040.nc" in names

    def test_two_scenarios_gives_four_files(self):
        names = _plugin_filenames(["ssp245", "ssp585"], [2040])
        assert len(names) == 4

    def test_two_horizons_gives_four_files(self):
        names = _plugin_filenames(["ssp245"], [2040, 2060])
        assert len(names) == 4


class TestPrepareDroughtStressData:
    def test_creates_output_file(self, cmip6_dir, out_dir):
        prepare_drought_stress_data(cmip6_dir, out_dir)
        assert (out_dir / "drought_stress_precip_ssp245_2040.nc").exists()

    def test_creates_output_dir_if_missing(self, cmip6_dir, out_dir):
        assert not out_dir.exists()
        prepare_drought_stress_data(cmip6_dir, out_dir)
        assert out_dir.exists()

    def test_returns_list_of_paths(self, cmip6_dir, out_dir):
        result = prepare_drought_stress_data(cmip6_dir, out_dir)
        assert isinstance(result, list)
        assert all(isinstance(p, Path) for p in result)

    def test_creates_all_found_scenarios(self, cmip6_dir, out_dir):
        result = prepare_drought_stress_data(cmip6_dir, out_dir)
        assert len(result) == 2

    def test_output_is_valid_netcdf(self, cmip6_dir, out_dir):
        prepare_drought_stress_data(cmip6_dir, out_dir)
        path = out_dir / "drought_stress_precip_ssp245_2040.nc"
        ds = xr.open_dataset(path)
        assert len(ds.data_vars) >= 1

    def test_skips_missing_source_file(self, tmp_path, out_dir):
        empty_src = tmp_path / "empty_cmip6"
        empty_src.mkdir()
        result = prepare_drought_stress_data(empty_src, out_dir)
        assert result == []


class TestPrepareHeatStressData:
    def test_creates_output_file(self, cmip6_dir, out_dir):
        prepare_heat_stress_data(cmip6_dir, out_dir)
        assert (out_dir / "heat_stress_mean_temp_ssp245_2040.nc").exists()

    def test_creates_output_dir_if_missing(self, cmip6_dir, out_dir):
        assert not out_dir.exists()
        prepare_heat_stress_data(cmip6_dir, out_dir)
        assert out_dir.exists()

    def test_returns_list_of_paths(self, cmip6_dir, out_dir):
        result = prepare_heat_stress_data(cmip6_dir, out_dir)
        assert isinstance(result, list)
        assert all(isinstance(p, Path) for p in result)

    def test_creates_all_found_scenarios(self, cmip6_dir, out_dir):
        result = prepare_heat_stress_data(cmip6_dir, out_dir)
        assert len(result) == 2

    def test_output_is_valid_netcdf(self, cmip6_dir, out_dir):
        prepare_heat_stress_data(cmip6_dir, out_dir)
        path = out_dir / "heat_stress_mean_temp_ssp245_2040.nc"
        ds = xr.open_dataset(path)
        assert len(ds.data_vars) >= 1

    def test_skips_missing_source_file(self, tmp_path, out_dir):
        empty_src = tmp_path / "empty_cmip6"
        empty_src.mkdir()
        result = prepare_heat_stress_data(empty_src, out_dir)
        assert result == []


class TestPrepareAllPluginData:
    def test_returns_dict_with_plugin_keys(self, cmip6_dir, out_dir):
        result = prepare_all_plugin_data(cmip6_dir, out_dir)
        assert "drought_stress" in result
        assert "heat_stress" in result

    def test_total_created_files(self, cmip6_dir, out_dir):
        result = prepare_all_plugin_data(cmip6_dir, out_dir)
        total = sum(len(v) for v in result.values())
        assert total == 4

    def test_all_output_files_exist(self, cmip6_dir, out_dir):
        result = prepare_all_plugin_data(cmip6_dir, out_dir)
        for paths in result.values():
            for p in paths:
                assert p.exists()
