"""Export a boolean zone mask (xr.DataArray with lat/lon coords) to MBTiles."""

import io
import math
import sqlite3
from pathlib import Path

import numpy as np
import xarray as xr
from PIL import Image

_DEFAULT_OUTPUT_DIR = Path(__file__).parents[1] / "data" / "mbtiles"
_TILE_SIZE = 256
GAIN_COLOR = (0, 200, 100, 180)
LOSS_COLOR = (220, 50, 50, 180)


def _tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """Return (west, south, east, north) in degrees for tile z/x/y (XYZ scheme)."""
    n = 2**z
    lon_w = x / n * 360 - 180
    lon_e = (x + 1) / n * 360 - 180
    lat_n = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    lat_s = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
    return lon_w, lat_s, lon_e, lat_n


def _tiles_for_bounds(west: float, south: float, east: float, north: float, zoom: int):
    """Yield (x, y) XYZ tile indices covering the bounding box at the given zoom."""
    n = 2**zoom

    def _tx(lon):
        return int((lon + 180) / 360 * n)

    def _ty(lat):
        lat_r = math.radians(max(-85.051129, min(85.051129, lat)))
        return int((1 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2 * n)

    x_min, x_max = _tx(west), _tx(east)
    y_min, y_max = _ty(north), _ty(south)  # y increases southward
    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            yield x, y


def _mask_to_rgba(
    mask: xr.DataArray,
    west: float,
    south: float,
    east: float,
    north: float,
    color: tuple[int, int, int, int],
    size: int = _TILE_SIZE,
) -> np.ndarray:
    """Render mask cells that fall within tile bounds to an RGBA array."""
    canvas = np.zeros((size, size, 4), dtype=np.uint8)

    lat_name = "lat" if "lat" in mask.coords else "latitude"
    lon_name = "lon" if "lon" in mask.coords else "longitude"

    if lat_name not in mask.coords or lon_name not in mask.coords:
        return canvas

    lat_vals = mask[lat_name].values
    lon_vals = mask[lon_name].values
    mask_arr = mask.values

    if east < lon_vals.min() or west > lon_vals.max():
        return canvas
    if north < lat_vals.min() or south > lat_vals.max():
        return canvas

    # Pixel centres in geographic coordinates (row 0 = northernmost)
    pixel_lats = north - (np.arange(size) + 0.5) * (north - south) / size
    pixel_lons = west + (np.arange(size) + 0.5) * (east - west) / size

    def _nearest(sorted_arr, orig_order, queries):
        idx = np.searchsorted(sorted_arr, queries).clip(1, len(sorted_arr) - 1)
        left = idx - 1
        closer = np.where(
            np.abs(sorted_arr[idx] - queries) < np.abs(sorted_arr[left] - queries), idx, left
        )
        return orig_order[closer]

    lat_order = np.argsort(lat_vals)
    lon_order = np.argsort(lon_vals)

    row_idx = _nearest(lat_vals[lat_order], lat_order, pixel_lats)
    col_idx = _nearest(lon_vals[lon_order], lon_order, pixel_lons)

    # Vectorised 2-D lookup
    pixel_values = mask_arr[row_idx[:, None], col_idx[None, :]]
    canvas[pixel_values > 0.5] = color
    return canvas


def _encode_png_rgba(rgba: np.ndarray) -> bytes:
    img = Image.fromarray(rgba.astype(np.uint8), mode="RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _init_mbtiles(
    path: Path,
    name: str,
    bounds: tuple[float, float, float, float],
    min_zoom: int,
    max_zoom: int,
) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS metadata (name TEXT, value TEXT)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tiles "
        "(zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS tile_index ON tiles (zoom_level, tile_column, tile_row)"
    )
    west, south, east, north = bounds
    conn.executemany(
        "INSERT OR REPLACE INTO metadata VALUES (?, ?)",
        [
            ("name", name),
            ("type", "overlay"),
            ("version", "1"),
            ("description", name),
            ("format", "png"),
            ("bounds", f"{west},{south},{east},{north}"),
            ("minzoom", str(min_zoom)),
            ("maxzoom", str(max_zoom)),
        ],
    )
    conn.commit()
    return conn


def export_mbtiles(
    mask: xr.DataArray,
    output_path: Path,
    name: str = "groundshift",
    color: tuple[int, int, int, int] = GAIN_COLOR,
    min_zoom: int = 4,
    max_zoom: int = 10,
) -> Path:
    lat_name = "lat" if "lat" in mask.coords else "latitude"
    lon_name = "lon" if "lon" in mask.coords else "longitude"

    west = float(mask[lon_name].min())
    east = float(mask[lon_name].max())
    south = float(mask[lat_name].min())
    north = float(mask[lat_name].max())

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    conn = _init_mbtiles(output_path, name, (west, south, east, north), min_zoom, max_zoom)

    for zoom in range(min_zoom, max_zoom + 1):
        for x, y in _tiles_for_bounds(west, south, east, north, zoom):
            t_west, t_south, t_east, t_north = _tile_bounds(zoom, x, y)
            rgba = _mask_to_rgba(mask, t_west, t_south, t_east, t_north, color)
            if not rgba.any():
                continue
            png = _encode_png_rgba(rgba)
            tms_y = (2**zoom - 1) - y  # MBTiles uses TMS (y flipped)
            conn.execute(
                "INSERT OR REPLACE INTO tiles VALUES (?, ?, ?, ?)",
                (zoom, x, tms_y, png),
            )

    conn.commit()
    conn.close()
    return output_path
