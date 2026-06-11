import sqlite3

import numpy as np
import pytest
import xarray as xr

from scripts.export_mbtiles import (
    _encode_png_rgba,
    _mask_to_rgba,
    _tile_bounds,
    _tiles_for_bounds,
    export_mbtiles,
)


def _mask_with_coords(shape=(4, 8), lat_range=(10, -10), lon_range=(-20, 20)):
    lats = np.linspace(lat_range[0], lat_range[1], shape[0])
    lons = np.linspace(lon_range[0], lon_range[1], shape[1])
    data = np.zeros(shape, dtype=float)
    data[1, 3] = 1.0  # one True cell near centre
    return xr.DataArray(data, coords={"lat": lats, "lon": lons}, dims=["lat", "lon"])


class TestTileBounds:
    def test_zoom0_covers_world_lon(self):
        west, _, east, _ = _tile_bounds(0, 0, 0)
        assert west == pytest.approx(-180, abs=1)
        assert east == pytest.approx(180, abs=1)

    def test_zoom0_covers_world_lat(self):
        _, south, _, north = _tile_bounds(0, 0, 0)
        assert south == pytest.approx(-85.05, abs=0.1)
        assert north == pytest.approx(85.05, abs=0.1)

    def test_zoom1_upper_left_lon(self):
        west, _, east, _ = _tile_bounds(1, 0, 0)
        assert west == pytest.approx(-180, abs=1)
        assert east == pytest.approx(0, abs=1)

    def test_zoom1_upper_left_is_northern_half(self):
        _, south, _, north = _tile_bounds(1, 0, 0)
        assert north > 0
        assert south >= 0

    def test_tile_width_halves_each_zoom(self):
        _, _, e0, _ = _tile_bounds(0, 0, 0)
        w0, _, _, _ = _tile_bounds(0, 0, 0)
        _, _, e1, _ = _tile_bounds(1, 0, 0)
        w1, _, _, _ = _tile_bounds(1, 0, 0)
        assert (e0 - w0) == pytest.approx(2 * (e1 - w1), rel=0.01)


class TestTilesForBounds:
    def test_small_area_returns_at_least_one_tile(self):
        tiles = list(_tiles_for_bounds(-1, -1, 1, 1, zoom=5))
        assert len(tiles) >= 1

    def test_returns_int_tuples(self):
        tiles = list(_tiles_for_bounds(-1, -1, 1, 1, zoom=5))
        for x, y in tiles:
            assert isinstance(x, int) and isinstance(y, int)

    def test_wider_area_gives_more_tiles(self):
        small = list(_tiles_for_bounds(-1, -1, 1, 1, zoom=8))
        large = list(_tiles_for_bounds(-20, -20, 20, 20, zoom=8))
        assert len(large) > len(small)

    def test_tile_x_y_are_non_negative(self):
        for x, y in _tiles_for_bounds(-10, -10, 10, 10, zoom=4):
            assert x >= 0 and y >= 0


class TestMaskToRgba:
    def test_returns_correct_shape(self):
        mask = _mask_with_coords()
        tile_bounds = _tile_bounds(3, 3, 3)
        rgba = _mask_to_rgba(mask, *tile_bounds, color=(0, 200, 100, 180))
        assert rgba.shape == (256, 256, 4)

    def test_out_of_bounds_tile_returns_transparent(self):
        mask = _mask_with_coords()
        # tile completely outside mask extent
        rgba = _mask_to_rgba(mask, 50, 50, 60, 60, color=(0, 200, 100, 180))
        assert rgba.sum() == 0

    def test_all_false_mask_returns_transparent(self):
        lats = np.linspace(10, -10, 4)
        lons = np.linspace(-20, 20, 8)
        mask = xr.DataArray(
            np.zeros((4, 8), dtype=float),
            coords={"lat": lats, "lon": lons},
            dims=["lat", "lon"],
        )
        rgba = _mask_to_rgba(mask, -20, -10, 20, 10, color=(0, 200, 100, 180))
        assert rgba.sum() == 0

    def test_true_cell_in_bounds_produces_colored_pixels(self):
        mask = _mask_with_coords()
        # bounds that definitely include our True cell at lat≈3.3, lon≈-2.9
        rgba = _mask_to_rgba(mask, -20, -10, 20, 10, color=(0, 200, 100, 180))
        assert rgba.sum() > 0

    def test_color_values_match_input(self):
        mask = _mask_with_coords()
        color = (255, 0, 128, 200)
        rgba = _mask_to_rgba(mask, -20, -10, 20, 10, color=color)
        colored = rgba[rgba[:, :, 3] > 0]
        assert colored.shape[0] > 0
        assert tuple(colored[0]) == color


class TestEncodePngRgba:
    def test_returns_bytes(self):
        rgba = np.zeros((256, 256, 4), dtype=np.uint8)
        result = _encode_png_rgba(rgba)
        assert isinstance(result, bytes)

    def test_has_png_signature(self):
        rgba = np.zeros((256, 256, 4), dtype=np.uint8)
        result = _encode_png_rgba(rgba)
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    def test_nonempty(self):
        rgba = np.zeros((256, 256, 4), dtype=np.uint8)
        assert len(_encode_png_rgba(rgba)) > 0

    def test_colored_png_larger_than_blank(self):
        blank = np.zeros((256, 256, 4), dtype=np.uint8)
        colored = blank.copy()
        colored[100:150, 100:150] = (0, 200, 100, 180)
        assert len(_encode_png_rgba(colored)) >= len(_encode_png_rgba(blank))


class TestExportMbtiles:
    def test_creates_output_file(self, tmp_path):
        out = export_mbtiles(_mask_with_coords(), tmp_path / "out.mbtiles", min_zoom=0, max_zoom=1)
        assert out.exists()

    def test_returns_output_path(self, tmp_path):
        expected = tmp_path / "layer.mbtiles"
        result = export_mbtiles(_mask_with_coords(), expected, min_zoom=0, max_zoom=1)
        assert result == expected

    def test_output_is_valid_sqlite(self, tmp_path):
        out = export_mbtiles(_mask_with_coords(), tmp_path / "out.mbtiles", min_zoom=0, max_zoom=1)
        conn = sqlite3.connect(out)
        conn.execute("SELECT count(*) FROM tiles")
        conn.close()

    def test_metadata_table_exists(self, tmp_path):
        out = export_mbtiles(_mask_with_coords(), tmp_path / "out.mbtiles", min_zoom=0, max_zoom=1)
        conn = sqlite3.connect(out)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        assert "metadata" in tables

    def test_metadata_name_stored(self, tmp_path):
        out = export_mbtiles(
            _mask_with_coords(), tmp_path / "out.mbtiles", name="test_layer", min_zoom=0, max_zoom=1
        )
        conn = sqlite3.connect(out)
        row = conn.execute("SELECT value FROM metadata WHERE name='name'").fetchone()
        conn.close()
        assert row[0] == "test_layer"

    def test_metadata_format_is_png(self, tmp_path):
        out = export_mbtiles(_mask_with_coords(), tmp_path / "out.mbtiles", min_zoom=0, max_zoom=1)
        conn = sqlite3.connect(out)
        row = conn.execute("SELECT value FROM metadata WHERE name='format'").fetchone()
        conn.close()
        assert row[0] == "png"

    def test_metadata_minzoom_stored(self, tmp_path):
        out = export_mbtiles(_mask_with_coords(), tmp_path / "out.mbtiles", min_zoom=2, max_zoom=4)
        conn = sqlite3.connect(out)
        row = conn.execute("SELECT value FROM metadata WHERE name='minzoom'").fetchone()
        conn.close()
        assert row[0] == "2"

    def test_metadata_maxzoom_stored(self, tmp_path):
        out = export_mbtiles(_mask_with_coords(), tmp_path / "out.mbtiles", min_zoom=2, max_zoom=4)
        conn = sqlite3.connect(out)
        row = conn.execute("SELECT value FROM metadata WHERE name='maxzoom'").fetchone()
        conn.close()
        assert row[0] == "4"

    def test_at_least_one_tile_written_for_mask_with_true_cells(self, tmp_path):
        out = export_mbtiles(_mask_with_coords(), tmp_path / "out.mbtiles", min_zoom=0, max_zoom=3)
        conn = sqlite3.connect(out)
        count = conn.execute("SELECT count(*) FROM tiles").fetchone()[0]
        conn.close()
        assert count > 0

    def test_tile_data_is_valid_png(self, tmp_path):
        out = export_mbtiles(_mask_with_coords(), tmp_path / "out.mbtiles", min_zoom=0, max_zoom=3)
        conn = sqlite3.connect(out)
        row = conn.execute("SELECT tile_data FROM tiles LIMIT 1").fetchone()
        conn.close()
        assert row[0][:8] == b"\x89PNG\r\n\x1a\n"

    def test_creates_parent_dirs(self, tmp_path):
        deep_path = tmp_path / "a" / "b" / "out.mbtiles"
        export_mbtiles(_mask_with_coords(), deep_path, min_zoom=0, max_zoom=1)
        assert deep_path.exists()
