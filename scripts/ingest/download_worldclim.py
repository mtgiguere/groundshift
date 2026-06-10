"""Download WorldClim v2.1 base data required by WorldClimSource.

Downloads two zip archives from the UC Davis geodata server and extracts
exactly the three files WorldClimSource needs:

  wc2.1_10m_bio_1.tif   — mean annual temperature (°C × 10)
  wc2.1_10m_bio_12.tif  — annual precipitation (mm)
  wc2.1_10m_elev.tif    — elevation (m)

Files land in data/worldclim/10m/ relative to the project root.
Re-running is safe — existing files are not re-downloaded.

Usage:
    python scripts/ingest/download_worldclim.py
"""

import urllib.request
import zipfile
from pathlib import Path

# WorldClim v2.1 files are served from UC Davis. Resolution "10m" (~340 km)
# is the coarsest available — fast to download, sufficient for regional
# crop suitability analysis. Finer resolutions (5m, 2.5m, 30s) follow the
# same URL pattern and file naming convention.
_BASE_URL = "https://geodata.ucdavis.edu/climate/worldclim/2_1/base"

# Hardcoded destination: base climate data always lives here.
# WorldClimSource is constructed with this path by convention.
DATA_DIR = Path(__file__).parents[2] / "data" / "worldclim" / "10m"


def _bio_url(resolution: str) -> str:
    return f"{_BASE_URL}/wc2.1_{resolution}_bio.zip"


def _elev_url(resolution: str) -> str:
    return f"{_BASE_URL}/wc2.1_{resolution}_elev.zip"


def _expected_filenames(resolution: str) -> list[str]:
    # Exactly the three files WorldClimSource needs — bio_1 (mean annual temp),
    # bio_12 (annual precipitation), and elev (altitude).
    return [
        f"wc2.1_{resolution}_bio_1.tif",
        f"wc2.1_{resolution}_bio_12.tif",
        f"wc2.1_{resolution}_elev.tif",
    ]


def _all_files_present(dest_dir: Path, resolution: str) -> bool:
    return all((dest_dir / name).exists() for name in _expected_filenames(resolution))


def _download_and_extract(url: str, members: list[str], dest_dir: Path) -> None:
    zip_path = dest_dir / "_tmp_download.zip"
    print(f"  Downloading {url} ...")
    urllib.request.urlretrieve(url, zip_path)  # noqa: S310 — URL is a hardcoded constant
    with zipfile.ZipFile(zip_path) as zf:
        for member in members:
            print(f"  Extracting {member}")
            zf.extract(member, dest_dir)
    zip_path.unlink()


def download_worldclim(dest_dir: Path = DATA_DIR, resolution: str = "10m") -> None:
    if _all_files_present(dest_dir, resolution):
        print(f"WorldClim data already present in {dest_dir} — nothing to do.")
        return

    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"Downloading WorldClim v2.1 ({resolution}) -> {dest_dir}")

    # Bio variables: the full zip contains all 19 bioclimatic variables;
    # we extract only bio_1 and bio_12.
    _download_and_extract(
        url=_bio_url(resolution),
        members=[
            f"wc2.1_{resolution}_bio_1.tif",
            f"wc2.1_{resolution}_bio_12.tif",
        ],
        dest_dir=dest_dir,
    )

    # Elevation: single-file zip.
    _download_and_extract(
        url=_elev_url(resolution),
        members=[f"wc2.1_{resolution}_elev.tif"],
        dest_dir=dest_dir,
    )

    print("Done.")


if __name__ == "__main__":
    download_worldclim()
