"""
Tests for ERA5Source.

Synthetic NetCDF files are written with ERA5's native coordinate names
(latitude/longitude, descending latitude) so the tests exercise the
real normalization path ERA5Source must perform.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.time_range import TimeRange

REGION = BoundingBox(min_lon=35.0, min_lat=3.0, max_lon=42.0, max_lat=15.0)
TIME_RANGE = TimeRange(start=datetime(2015, 1, 1), end=datetime(2024, 12, 31))

# Synthetic grid covering a superset of REGION; latitude descending as in ERA5.
_LONS = np.linspace(25.0, 55.0, 61)  # 0.5° resolution
_LATS = np.linspace(20.0, -5.0, 51)  # descending, like ERA5


def _write_nc(path: Path, fill_value: float) -> None:
    data = np.full((len(_LATS), len(_LONS)), fill_value, dtype="float32")
    da = xr.DataArray(
        data,
        dims=["latitude", "longitude"],
        coords={"latitude": _LATS, "longitude": _LONS},
    )
    da.to_netcdf(path)


@pytest.fixture
def era5_dir(tmp_path: Path) -> Path:
    _write_nc(tmp_path / "era5_mean_annual_temp_c.nc", fill_value=19.5)
    _write_nc(tmp_path / "era5_annual_precipitation_mm.nc", fill_value=1800.0)
    _write_nc(tmp_path / "era5_altitude_m.nc", fill_value=950.0)
    return tmp_path


def _make_source(base_dir: Path):
    from groundshift.core.envelope.era5_source import ERA5Source

    return ERA5Source(base_dir)


def test_fetch_returns_dataarray(era5_dir):
    source = _make_source(era5_dir)
    result = source.fetch("mean_annual_temp_c", REGION, TIME_RANGE)
    assert isinstance(result, xr.DataArray)


def test_fetch_clips_to_region(era5_dir):
    source = _make_source(era5_dir)
    result = source.fetch("mean_annual_temp_c", REGION, TIME_RANGE)
    assert float(result.x.min()) >= REGION.min_lon
    assert float(result.x.max()) <= REGION.max_lon
    assert float(result.y.min()) >= REGION.min_lat
    assert float(result.y.max()) <= REGION.max_lat


def test_fetch_uses_x_y_coordinate_names(era5_dir):
    # All ClimateDataSource implementations must return x/y coords so the
    # rest of the pipeline (anchor scorer, envelope scorer) works consistently.
    source = _make_source(era5_dir)
    result = source.fetch("mean_annual_temp_c", REGION, TIME_RANGE)
    assert "x" in result.dims or "x" in result.coords
    assert "y" in result.dims or "y" in result.coords
    assert "latitude" not in result.coords
    assert "longitude" not in result.coords


def test_fetch_preserves_fill_value_for_temp(era5_dir):
    source = _make_source(era5_dir)
    result = source.fetch("mean_annual_temp_c", REGION, TIME_RANGE)
    assert float(result.mean()) == pytest.approx(19.5, abs=1e-3)


def test_fetch_preserves_fill_value_for_precip(era5_dir):
    source = _make_source(era5_dir)
    result = source.fetch("annual_precipitation_mm", REGION, TIME_RANGE)
    assert float(result.mean()) == pytest.approx(1800.0, abs=1e-3)


def test_fetch_preserves_fill_value_for_elevation(era5_dir):
    source = _make_source(era5_dir)
    result = source.fetch("altitude_m", REGION, TIME_RANGE)
    assert float(result.mean()) == pytest.approx(950.0, abs=1e-3)


def test_fetch_unknown_variable_raises_key_error(era5_dir):
    source = _make_source(era5_dir)
    with pytest.raises(KeyError, match="unknown_var"):
        source.fetch("unknown_var", REGION, TIME_RANGE)


def test_fetch_missing_file_raises_file_not_found_error(tmp_path):
    source = _make_source(tmp_path)  # empty dir — no files written
    with pytest.raises(FileNotFoundError):
        source.fetch("mean_annual_temp_c", REGION, TIME_RANGE)
