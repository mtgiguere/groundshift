"""Export a boolean zone mask (xr.DataArray with lat/lon coords) to KMZ."""

import io
import zipfile
from pathlib import Path

import xarray as xr

_DEFAULT_OUTPUT_DIR = Path(__file__).parents[1] / "data" / "kmz"

# KML uses ABGR hex: alpha, blue, green, red
GAIN_COLOR = "b200c864"  # semi-transparent green
LOSS_COLOR = "b23232dc"  # semi-transparent red


def _cell_polygon_coords(lat: float, lon: float, dlat: float, dlon: float) -> str:
    """Return KML coordinate string for a rectangular cell (closed ring, 5 points)."""
    w = lon - dlon / 2
    e = lon + dlon / 2
    s = lat - dlat / 2
    n = lat + dlat / 2
    pairs = [
        f"{w},{s},0",
        f"{e},{s},0",
        f"{e},{n},0",
        f"{w},{n},0",
        f"{w},{s},0",
    ]
    return " ".join(pairs)


def _make_kml(
    mask: xr.DataArray,
    name: str,
    color: str,
) -> bytes:
    lat_name = "lat" if "lat" in mask.coords else "latitude"
    lon_name = "lon" if "lon" in mask.coords else "longitude"

    lat_vals = mask[lat_name].values
    lon_vals = mask[lon_name].values
    mask_arr = mask.values

    dlat = abs(float(lat_vals[1] - lat_vals[0])) if len(lat_vals) > 1 else 1.0
    dlon = abs(float(lon_vals[1] - lon_vals[0])) if len(lon_vals) > 1 else 1.0

    placemarks = []
    for i, lat in enumerate(lat_vals):
        for j, lon in enumerate(lon_vals):
            if mask_arr[i, j] <= 0.5:
                continue
            coords = _cell_polygon_coords(float(lat), float(lon), dlat, dlon)
            placemarks.append(
                f"    <Placemark>\n"
                f"      <styleUrl>#zone_style</styleUrl>\n"
                f"      <Polygon><outerBoundaryIs><LinearRing>"
                f"<coordinates>{coords}</coordinates>"
                f"</LinearRing></outerBoundaryIs></Polygon>\n"
                f"    </Placemark>"
            )

    kml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
        "  <Document>\n"
        f"    <name>{name}</name>\n"
        f'    <Style id="zone_style">\n'
        f"      <PolyStyle><color>{color}</color></PolyStyle>\n"
        f"      <LineStyle><color>{color}</color><width>0.5</width></LineStyle>\n"
        f"    </Style>\n" + "\n".join(placemarks) + "\n  </Document>\n</kml>\n"
    )
    return kml.encode("utf-8")


def export_kmz(
    mask: xr.DataArray,
    output_path: Path,
    name: str = "groundshift",
    color: str = GAIN_COLOR,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    kml_bytes = _make_kml(mask, name=name, color=color)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("doc.kml", kml_bytes)
    output_path.write_bytes(buf.getvalue())
    return output_path
