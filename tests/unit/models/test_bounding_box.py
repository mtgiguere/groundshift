import pytest

from groundshift.models.bounding_box import BoundingBox


def test_bounding_box_stores_coordinates():
    bbox = BoundingBox(min_lon=35.0, min_lat=3.0, max_lon=42.0, max_lat=15.0)
    assert bbox.min_lon == 35.0
    assert bbox.min_lat == 3.0
    assert bbox.max_lon == 42.0
    assert bbox.max_lat == 15.0


def test_bounding_box_default_crs_is_wgs84():
    bbox = BoundingBox(min_lon=35.0, min_lat=3.0, max_lon=42.0, max_lat=15.0)
    assert bbox.crs == "EPSG:4326"


def test_bounding_box_raises_if_min_lon_exceeds_max_lon():
    with pytest.raises(ValueError, match="min_lon"):
        BoundingBox(min_lon=42.0, min_lat=3.0, max_lon=35.0, max_lat=15.0)


def test_bounding_box_raises_if_min_lat_exceeds_max_lat():
    with pytest.raises(ValueError, match="min_lat"):
        BoundingBox(min_lon=35.0, min_lat=15.0, max_lon=42.0, max_lat=3.0)


def test_bounding_box_raises_if_longitude_out_of_range():
    with pytest.raises(ValueError, match="longitude"):
        BoundingBox(min_lon=-181.0, min_lat=3.0, max_lon=42.0, max_lat=15.0)


def test_bounding_box_raises_if_latitude_out_of_range():
    with pytest.raises(ValueError, match="latitude"):
        BoundingBox(min_lon=35.0, min_lat=-91.0, max_lon=42.0, max_lat=15.0)
