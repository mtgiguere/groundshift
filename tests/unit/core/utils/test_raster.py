import geopandas as gpd
import pytest
import xarray as xr
from shapely.geometry import box

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.suitability_modifier import SuitabilityModifier

REGION = BoundingBox(min_lon=35.0, min_lat=3.0, max_lon=42.0, max_lat=15.0)
RESOLUTION = 1.0  # 1-degree grid for easy shape arithmetic


def _make_gdf(factor: float, geom=None) -> gpd.GeoDataFrame:
    if geom is None:
        geom = box(36.0, 4.0, 40.0, 12.0)  # polygon inside REGION
    return gpd.GeoDataFrame({"factor": [factor]}, geometry=[geom], crs="EPSG:4326")


def _call(gdf, **kwargs):
    from groundshift.core.utils.raster import geodataframe_to_modifier

    defaults = dict(
        factor_column="factor",
        plugin_id="test",
        region=REGION,
        resolution_deg=RESOLUTION,
        metadata={"threat_tier": "stress"},
    )
    defaults.update(kwargs)
    return geodataframe_to_modifier(gdf, **defaults)


def test_returns_suitability_modifier():
    result = _call(_make_gdf(0.8))
    assert isinstance(result, SuitabilityModifier)


def test_output_fields_are_dataarrays():
    result = _call(_make_gdf(0.8))
    assert isinstance(result.factor_value, xr.DataArray)
    assert isinstance(result.probability, xr.DataArray)
    assert isinstance(result.confidence, xr.DataArray)


def test_grid_shape_matches_region_and_resolution():
    result = _call(_make_gdf(0.8))
    nrows = int((REGION.max_lat - REGION.min_lat) / RESOLUTION)
    ncols = int((REGION.max_lon - REGION.min_lon) / RESOLUTION)
    assert result.factor_value.shape == (nrows, ncols)


def test_covered_cells_have_factor_value():
    # Polygon covers entire region → all cells should equal the factor
    full_poly = box(REGION.min_lon, REGION.min_lat, REGION.max_lon, REGION.max_lat)
    gdf = gpd.GeoDataFrame({"factor": [0.6]}, geometry=[full_poly], crs="EPSG:4326")
    result = _call(gdf)
    assert float(result.factor_value.mean()) == pytest.approx(0.6, abs=1e-3)


def test_uncovered_cells_are_zero():
    # Polygon outside REGION entirely → all cells should be 0.0
    outside_poly = box(0.0, 0.0, 1.0, 1.0)
    gdf = gpd.GeoDataFrame({"factor": [0.9]}, geometry=[outside_poly], crs="EPSG:4326")
    result = _call(gdf)
    assert float(result.factor_value.max()) == pytest.approx(0.0)


def test_probability_broadcasts_to_dataarray():
    result = _call(_make_gdf(0.8), probability=0.7)
    assert isinstance(result.probability, xr.DataArray)
    assert float(result.probability.mean()) == pytest.approx(0.7)
    assert result.probability.shape == result.factor_value.shape


def test_confidence_broadcasts_to_dataarray():
    result = _call(_make_gdf(0.8), confidence=0.9)
    assert isinstance(result.confidence, xr.DataArray)
    assert float(result.confidence.mean()) == pytest.approx(0.9)
    assert result.confidence.shape == result.factor_value.shape


def test_plugin_id_is_preserved():
    result = _call(_make_gdf(0.8), plugin_id="my_plugin")
    assert result.plugin_id == "my_plugin"


def test_metadata_is_preserved():
    result = _call(_make_gdf(0.8), metadata={"threat_tier": "existential"})
    assert result.metadata["threat_tier"] == "existential"


def test_non_wgs84_crs_raises_value_error():
    gdf = gpd.GeoDataFrame(
        {"factor": [0.8]},
        geometry=[box(36.0, 4.0, 40.0, 12.0)],
        crs="EPSG:32637",  # UTM zone 37N
    )
    with pytest.raises(ValueError, match="EPSG:4326"):
        _call(gdf)


def test_missing_factor_column_raises_key_error():
    gdf = gpd.GeoDataFrame(
        {"severity": [0.8]},
        geometry=[box(36.0, 4.0, 40.0, 12.0)],
        crs="EPSG:4326",
    )
    with pytest.raises(KeyError):
        _call(gdf, factor_column="factor")
