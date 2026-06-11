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
TIME_RANGE = TimeRange(start=datetime(1985, 1, 1), end=datetime(2024, 12, 31))


def _write_tif(path: Path, fill_value: float) -> None:
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
def landsat_dir(tmp_path: Path) -> Path:
    _write_tif(tmp_path / "landsat_ndvi_trend.tif", fill_value=-0.003)
    return tmp_path


def _make_source(base_dir: Path):
    from groundshift.core.imagery.landsat_source import LandsatSource

    return LandsatSource(base_dir)


def test_fetch_returns_dataarray(landsat_dir):
    source = _make_source(landsat_dir)
    result = source.fetch("ndvi_trend", REGION, TIME_RANGE)
    assert isinstance(result, xr.DataArray)


def test_fetch_clips_to_region(landsat_dir):
    source = _make_source(landsat_dir)
    result = source.fetch("ndvi_trend", REGION, TIME_RANGE)
    assert float(result.x.min()) >= REGION.min_lon
    assert float(result.x.max()) <= REGION.max_lon
    assert float(result.y.min()) >= REGION.min_lat
    assert float(result.y.max()) <= REGION.max_lat


def test_fetch_preserves_fill_value(landsat_dir):
    source = _make_source(landsat_dir)
    result = source.fetch("ndvi_trend", REGION, TIME_RANGE)
    assert float(result.mean()) == pytest.approx(-0.003, abs=1e-4)


def test_fetch_unknown_variable_raises_key_error(landsat_dir):
    source = _make_source(landsat_dir)
    with pytest.raises(KeyError, match="unknown_var"):
        source.fetch("unknown_var", REGION, TIME_RANGE)


def test_fetch_missing_file_raises_file_not_found_error(tmp_path):
    source = _make_source(tmp_path)
    with pytest.raises(FileNotFoundError):
        source.fetch("ndvi_trend", REGION, TIME_RANGE)


def test_landsat_source_is_imagery_source(landsat_dir):
    from groundshift.core.imagery.imagery_source import ImagerySource
    from groundshift.core.imagery.landsat_source import LandsatSource

    assert issubclass(LandsatSource, ImagerySource)
