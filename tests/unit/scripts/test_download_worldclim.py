from pathlib import Path

from scripts.ingest.download_worldclim import (
    _all_files_present,
    _bio_url,
    _elev_url,
    _expected_filenames,
)


def test_bio_url_points_to_ucdavis_for_10m_resolution():
    url = _bio_url("10m")
    assert "geodata.ucdavis.edu" in url
    assert "10m" in url
    assert url.endswith(".zip")


def test_elev_url_points_to_ucdavis_for_10m_resolution():
    url = _elev_url("10m")
    assert "geodata.ucdavis.edu" in url
    assert "10m" in url
    assert url.endswith(".zip")


def test_expected_filenames_are_exactly_what_worldclim_source_needs():
    # WorldClimSource maps: mean_annual_temp_c → bio_1,
    #                       annual_precipitation_mm → bio_12,
    #                       altitude_m → elev
    # The download must produce exactly these three files — no more, no less.
    assert set(_expected_filenames("10m")) == {
        "wc2.1_10m_bio_1.tif",
        "wc2.1_10m_bio_12.tif",
        "wc2.1_10m_elev.tif",
    }


def test_all_files_present_returns_true_when_all_exist(tmp_path: Path):
    for name in _expected_filenames("10m"):
        (tmp_path / name).touch()
    assert _all_files_present(tmp_path, "10m")


def test_all_files_present_returns_false_when_one_missing(tmp_path: Path):
    (tmp_path / "wc2.1_10m_bio_1.tif").touch()
    (tmp_path / "wc2.1_10m_bio_12.tif").touch()
    # elev is absent
    assert not _all_files_present(tmp_path, "10m")
