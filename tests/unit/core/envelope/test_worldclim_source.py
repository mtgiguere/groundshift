from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
import rasterio
import xarray as xr
from rasterio.crs import CRS
from rasterio.transform import from_bounds

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.time_range import TimeRange

REGION = BoundingBox(min_lon=35.0, min_lat=3.0, max_lon=42.0, max_lat=15.0)
TIME_RANGE = TimeRange(start=datetime(2020, 1, 1), end=datetime(2021, 1, 1))
RESOLUTION = "10m"


def _write_tif(path: Path, fill_value: float) -> None:
    """Write a synthetic single-band GeoTIFF covering a superset of REGION."""
    transform = from_bounds(30.0, -5.0, 50.0, 20.0, 200, 250)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=250,
        width=200,
        count=1,
        dtype="float32",
        crs=CRS.from_epsg(4326),
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        dst.write(np.full((1, 250, 200), fill_value, dtype="float32"))


@pytest.fixture
def worldclim_dir(tmp_path: Path) -> Path:
    _write_tif(tmp_path / f"wc2.1_{RESOLUTION}_bio_1.tif", fill_value=21.0)
    _write_tif(tmp_path / f"wc2.1_{RESOLUTION}_bio_12.tif", fill_value=2000.0)
    _write_tif(tmp_path / f"wc2.1_{RESOLUTION}_elev.tif", fill_value=1200.0)
    return tmp_path


def _make_source(base_dir: Path):
    from groundshift.core.envelope.worldclim_source import WorldClimSource

    return WorldClimSource(base_dir, resolution=RESOLUTION)


def test_fetch_returns_dataarray(worldclim_dir):
    source = _make_source(worldclim_dir)
    result = source.fetch("mean_annual_temp_c", REGION, TIME_RANGE)
    assert isinstance(result, xr.DataArray)


def test_fetch_clips_to_region(worldclim_dir):
    source = _make_source(worldclim_dir)
    result = source.fetch("mean_annual_temp_c", REGION, TIME_RANGE)
    assert float(result.x.min()) >= REGION.min_lon
    assert float(result.x.max()) <= REGION.max_lon
    assert float(result.y.min()) >= REGION.min_lat
    assert float(result.y.max()) <= REGION.max_lat


def test_fetch_preserves_fill_value_for_temp(worldclim_dir):
    source = _make_source(worldclim_dir)
    result = source.fetch("mean_annual_temp_c", REGION, TIME_RANGE)
    assert float(result.mean()) == pytest.approx(21.0, abs=1e-3)


def test_fetch_preserves_fill_value_for_precip(worldclim_dir):
    source = _make_source(worldclim_dir)
    result = source.fetch("annual_precipitation_mm", REGION, TIME_RANGE)
    assert float(result.mean()) == pytest.approx(2000.0, abs=1e-3)


def test_fetch_preserves_fill_value_for_elevation(worldclim_dir):
    source = _make_source(worldclim_dir)
    result = source.fetch("altitude_m", REGION, TIME_RANGE)
    assert float(result.mean()) == pytest.approx(1200.0, abs=1e-3)


def test_fetch_unknown_variable_raises_key_error(worldclim_dir):
    source = _make_source(worldclim_dir)
    with pytest.raises(KeyError, match="unknown_var"):
        source.fetch("unknown_var", REGION, TIME_RANGE)


def test_fetch_missing_file_raises_file_not_found_error(tmp_path):
    source = _make_source(tmp_path)  # empty dir — no files written
    with pytest.raises(FileNotFoundError):
        source.fetch("mean_annual_temp_c", REGION, TIME_RANGE)


def test_default_resolution_is_10m(worldclim_dir):
    from groundshift.core.envelope.worldclim_source import WorldClimSource

    source = WorldClimSource(worldclim_dir)
    result = source.fetch("mean_annual_temp_c", REGION, TIME_RANGE)
    assert isinstance(result, xr.DataArray)
