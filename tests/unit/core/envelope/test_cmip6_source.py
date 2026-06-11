"""
Tests for CMIP6Source.

Synthetic NetCDF files are written with CMIP6's native coordinate names
(lat/lon, descending lat) so the tests exercise the real normalization path.
Files are named cmip6_{variable}_{scenario}_{horizon_year}.nc.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from groundshift.core.envelope.climate_source import ClimateDataSource
from groundshift.models.bounding_box import BoundingBox
from groundshift.models.time_range import TimeRange

REGION = BoundingBox(min_lon=35.0, min_lat=3.0, max_lon=42.0, max_lat=15.0)

# CMIP6Source requires scenario and horizon_year on TimeRange.
TIME_RANGE_SSP245_2040 = TimeRange(
    start=datetime(2031, 1, 1),
    end=datetime(2040, 12, 31),
    scenario="ssp245",
    horizon_year=2040,
)
TIME_RANGE_SSP585_2100 = TimeRange(
    start=datetime(2091, 1, 1),
    end=datetime(2100, 12, 31),
    scenario="ssp585",
    horizon_year=2100,
)

_LONS = np.linspace(25.0, 55.0, 61)
_LATS = np.linspace(20.0, -5.0, 51)  # descending, like CMIP6 outputs


def _write_nc(path: Path, fill_value: float) -> None:
    data = np.full((len(_LATS), len(_LONS)), fill_value, dtype="float32")
    da = xr.DataArray(
        data,
        dims=["lat", "lon"],
        coords={"lat": _LATS, "lon": _LONS},
    )
    da.to_netcdf(path)


@pytest.fixture
def cmip6_dir(tmp_path: Path) -> Path:
    _write_nc(tmp_path / "cmip6_mean_annual_temp_c_ssp245_2040.nc", fill_value=22.5)
    _write_nc(tmp_path / "cmip6_mean_annual_temp_c_ssp585_2100.nc", fill_value=26.0)
    _write_nc(tmp_path / "cmip6_annual_precipitation_mm_ssp245_2040.nc", fill_value=1600.0)
    _write_nc(tmp_path / "cmip6_annual_precipitation_mm_ssp585_2100.nc", fill_value=1400.0)
    return tmp_path


def _make_source(base_dir: Path):
    from groundshift.core.envelope.cmip6_source import CMIP6Source

    return CMIP6Source(base_dir)


def test_fetch_returns_dataarray(cmip6_dir):
    source = _make_source(cmip6_dir)
    result = source.fetch("mean_annual_temp_c", REGION, TIME_RANGE_SSP245_2040)
    assert isinstance(result, xr.DataArray)


def test_fetch_clips_to_region(cmip6_dir):
    source = _make_source(cmip6_dir)
    result = source.fetch("mean_annual_temp_c", REGION, TIME_RANGE_SSP245_2040)
    assert float(result.x.min()) >= REGION.min_lon
    assert float(result.x.max()) <= REGION.max_lon
    assert float(result.y.min()) >= REGION.min_lat
    assert float(result.y.max()) <= REGION.max_lat


def test_fetch_uses_x_y_coordinate_names(cmip6_dir):
    source = _make_source(cmip6_dir)
    result = source.fetch("mean_annual_temp_c", REGION, TIME_RANGE_SSP245_2040)
    assert "x" in result.dims or "x" in result.coords
    assert "y" in result.dims or "y" in result.coords
    assert "lat" not in result.coords
    assert "lon" not in result.coords


def test_fetch_selects_ssp245_2040_file(cmip6_dir):
    source = _make_source(cmip6_dir)
    result = source.fetch("mean_annual_temp_c", REGION, TIME_RANGE_SSP245_2040)
    assert float(result.mean()) == pytest.approx(22.5, abs=1e-3)


def test_fetch_selects_ssp585_2100_file(cmip6_dir):
    source = _make_source(cmip6_dir)
    result = source.fetch("mean_annual_temp_c", REGION, TIME_RANGE_SSP585_2100)
    assert float(result.mean()) == pytest.approx(26.0, abs=1e-3)


def test_fetch_different_scenarios_return_different_values(cmip6_dir):
    # SSP5-8.5 at 2100 should be warmer than SSP2-4.5 at 2040 in our synthetic data.
    source = _make_source(cmip6_dir)
    r245 = source.fetch("mean_annual_temp_c", REGION, TIME_RANGE_SSP245_2040)
    r585 = source.fetch("mean_annual_temp_c", REGION, TIME_RANGE_SSP585_2100)
    assert float(r585.mean()) > float(r245.mean())


def test_fetch_raises_value_error_when_scenario_not_set(cmip6_dir):
    source = _make_source(cmip6_dir)
    no_scenario = TimeRange(start=datetime(2031, 1, 1), end=datetime(2040, 12, 31))
    with pytest.raises(ValueError, match="scenario"):
        source.fetch("mean_annual_temp_c", REGION, no_scenario)


def test_fetch_raises_value_error_when_horizon_not_set(cmip6_dir):
    source = _make_source(cmip6_dir)
    no_horizon = TimeRange(
        start=datetime(2031, 1, 1),
        end=datetime(2040, 12, 31),
        scenario="ssp245",
    )
    with pytest.raises(ValueError, match="horizon_year"):
        source.fetch("mean_annual_temp_c", REGION, no_horizon)


def test_fetch_raises_key_error_for_unknown_variable(cmip6_dir):
    source = _make_source(cmip6_dir)
    with pytest.raises(KeyError, match="unknown_var"):
        source.fetch("unknown_var", REGION, TIME_RANGE_SSP245_2040)


def test_fetch_raises_file_not_found_when_file_missing(tmp_path):
    source = _make_source(tmp_path)  # empty dir — no files written
    with pytest.raises(FileNotFoundError):
        source.fetch("mean_annual_temp_c", REGION, TIME_RANGE_SSP245_2040)


def test_cmip6_source_is_climate_data_source(cmip6_dir):
    from groundshift.core.envelope.cmip6_source import CMIP6Source

    assert issubclass(CMIP6Source, ClimateDataSource)
