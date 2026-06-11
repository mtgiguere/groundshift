import zipfile

import numpy as np
import xarray as xr

from scripts.export_kmz import (
    GAIN_COLOR,
    LOSS_COLOR,
    _cell_polygon_coords,
    _make_kml,
    export_kmz,
)


def _mask_with_coords(shape=(4, 8), lat_range=(10, -10), lon_range=(-20, 20)):
    lats = np.linspace(lat_range[0], lat_range[1], shape[0])
    lons = np.linspace(lon_range[0], lon_range[1], shape[1])
    data = np.zeros(shape, dtype=float)
    data[1, 3] = 1.0
    data[2, 5] = 1.0
    return xr.DataArray(data, coords={"lat": lats, "lon": lons}, dims=["lat", "lon"])


def _all_false_mask():
    lats = np.linspace(10, -10, 4)
    lons = np.linspace(-20, 20, 8)
    return xr.DataArray(
        np.zeros((4, 8), dtype=float),
        coords={"lat": lats, "lon": lons},
        dims=["lat", "lon"],
    )


class TestCellPolygonCoords:
    def test_returns_string(self):
        result = _cell_polygon_coords(10.0, -20.0, 5.0, 5.0)
        assert isinstance(result, str)

    def test_contains_five_coordinate_pairs(self):
        # KML LinearRing closes on itself: 5 pairs for a rectangle
        result = _cell_polygon_coords(10.0, -20.0, 5.0, 5.0)
        pairs = result.strip().split()
        assert len(pairs) == 5

    def test_first_and_last_coords_match(self):
        result = _cell_polygon_coords(10.0, -20.0, 5.0, 5.0)
        pairs = result.strip().split()
        assert pairs[0] == pairs[-1]

    def test_coords_are_lon_lat_format(self):
        # KML coordinates are lon,lat,alt
        result = _cell_polygon_coords(0.0, 0.0, 1.0, 1.0)
        first = result.strip().split()[0]
        parts = first.split(",")
        assert len(parts) >= 2


class TestMakeKml:
    def test_returns_bytes(self):
        mask = _mask_with_coords()
        result = _make_kml(mask, name="test", color=GAIN_COLOR)
        assert isinstance(result, bytes)

    def test_starts_with_xml_declaration(self):
        mask = _mask_with_coords()
        result = _make_kml(mask, name="test", color=GAIN_COLOR)
        assert result.startswith(b"<?xml")

    def test_contains_kml_namespace(self):
        mask = _mask_with_coords()
        result = _make_kml(mask, name="test", color=GAIN_COLOR)
        assert b"opengis.net/kml" in result

    def test_contains_document_name(self):
        mask = _mask_with_coords()
        result = _make_kml(mask, name="my_layer", color=GAIN_COLOR)
        assert b"my_layer" in result

    def test_contains_placemark_for_each_true_cell(self):
        mask = _mask_with_coords()  # 2 True cells
        result = _make_kml(mask, name="test", color=GAIN_COLOR)
        assert result.count(b"<Placemark>") == 2

    def test_all_false_mask_has_no_placemarks(self):
        mask = _all_false_mask()
        result = _make_kml(mask, name="test", color=GAIN_COLOR)
        assert b"<Placemark>" not in result

    def test_color_appears_in_kml(self):
        mask = _mask_with_coords()
        result = _make_kml(mask, name="test", color="b264c800")
        assert b"b264c800" in result

    def test_loss_color_differs_from_gain_color(self):
        assert GAIN_COLOR != LOSS_COLOR


class TestExportKmz:
    def test_creates_output_file(self, tmp_path):
        out = export_kmz(_mask_with_coords(), tmp_path / "test.kmz")
        assert out.exists()

    def test_returns_output_path(self, tmp_path):
        expected = tmp_path / "layer.kmz"
        result = export_kmz(_mask_with_coords(), expected)
        assert result == expected

    def test_output_is_valid_zip(self, tmp_path):
        out = export_kmz(_mask_with_coords(), tmp_path / "test.kmz")
        assert zipfile.is_zipfile(out)

    def test_zip_contains_doc_kml(self, tmp_path):
        out = export_kmz(_mask_with_coords(), tmp_path / "test.kmz")
        with zipfile.ZipFile(out) as zf:
            assert "doc.kml" in zf.namelist()

    def test_kml_inside_zip_is_valid_xml(self, tmp_path):
        out = export_kmz(_mask_with_coords(), tmp_path / "test.kmz")
        with zipfile.ZipFile(out) as zf:
            content = zf.read("doc.kml")
        assert content.startswith(b"<?xml")
        assert b"<kml" in content

    def test_kml_contains_placemarks_for_true_cells(self, tmp_path):
        out = export_kmz(_mask_with_coords(), tmp_path / "test.kmz")
        with zipfile.ZipFile(out) as zf:
            content = zf.read("doc.kml")
        assert content.count(b"<Placemark>") == 2

    def test_all_false_mask_still_creates_valid_kmz(self, tmp_path):
        out = export_kmz(_all_false_mask(), tmp_path / "empty.kmz")
        assert zipfile.is_zipfile(out)

    def test_creates_parent_dirs(self, tmp_path):
        deep_path = tmp_path / "a" / "b" / "out.kmz"
        export_kmz(_mask_with_coords(), deep_path)
        assert deep_path.exists()

    def test_name_appears_in_kml(self, tmp_path):
        out = export_kmz(_mask_with_coords(), tmp_path / "test.kmz", name="coffee_emerging")
        with zipfile.ZipFile(out) as zf:
            content = zf.read("doc.kml")
        assert b"coffee_emerging" in content
