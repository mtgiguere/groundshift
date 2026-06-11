import sqlite3

import pytest
from fastapi.testclient import TestClient


def _make_mbtiles(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE metadata (name TEXT, value TEXT)")
    conn.execute(
        "CREATE TABLE tiles "
        "(zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB)"
    )
    conn.executemany(
        "INSERT INTO metadata VALUES (?, ?)",
        [("name", "test"), ("format", "png"), ("minzoom", "0"), ("maxzoom", "3")],
    )
    conn.commit()
    conn.close()


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    from groundshift.api.app import create_app

    mbtiles_dir = tmp_path_factory.mktemp("mbtiles")
    _make_mbtiles(mbtiles_dir / "coffee_ethiopia.mbtiles")
    _make_mbtiles(mbtiles_dir / "coffee_colombia.mbtiles")
    _make_mbtiles(mbtiles_dir / "tea_india.mbtiles")
    return TestClient(create_app(mbtiles_dir=mbtiles_dir))


@pytest.fixture(scope="module")
def empty_client(tmp_path_factory):
    from groundshift.api.app import create_app

    mbtiles_dir = tmp_path_factory.mktemp("mbtiles_empty")
    return TestClient(create_app(mbtiles_dir=mbtiles_dir))


class TestPackagesListEndpoint:
    def test_returns_200(self, client):
        r = client.get("/api/v1/packages")
        assert r.status_code == 200

    def test_empty_dir_returns_200(self, empty_client):
        r = empty_client.get("/api/v1/packages")
        assert r.status_code == 200

    def test_response_has_packages_list(self, client):
        r = client.get("/api/v1/packages")
        assert isinstance(r.json()["packages"], list)

    def test_response_has_total(self, client):
        r = client.get("/api/v1/packages")
        assert "total" in r.json()

    def test_total_matches_package_count(self, client):
        r = client.get("/api/v1/packages")
        data = r.json()
        assert data["total"] == len(data["packages"])

    def test_all_three_packages_listed(self, client):
        r = client.get("/api/v1/packages")
        assert r.json()["total"] == 3

    def test_empty_dir_total_is_zero(self, empty_client):
        r = empty_client.get("/api/v1/packages")
        assert r.json()["total"] == 0

    def test_package_has_crop_id(self, client):
        r = client.get("/api/v1/packages")
        assert "crop_id" in r.json()["packages"][0]

    def test_package_has_region_id(self, client):
        r = client.get("/api/v1/packages")
        assert "region_id" in r.json()["packages"][0]

    def test_package_has_size_bytes(self, client):
        r = client.get("/api/v1/packages")
        assert "size_bytes" in r.json()["packages"][0]

    def test_size_bytes_is_positive_int(self, client):
        r = client.get("/api/v1/packages")
        size = r.json()["packages"][0]["size_bytes"]
        assert isinstance(size, int) and size > 0

    def test_filter_by_crop_id(self, client):
        r = client.get("/api/v1/packages?crop_id=coffee")
        assert r.status_code == 200
        pkgs = r.json()["packages"]
        assert all(p["crop_id"] == "coffee" for p in pkgs)
        assert len(pkgs) == 2

    def test_filter_by_region_id(self, client):
        r = client.get("/api/v1/packages?region_id=ethiopia")
        assert r.status_code == 200
        pkgs = r.json()["packages"]
        assert all(p["region_id"] == "ethiopia" for p in pkgs)
        assert len(pkgs) == 1

    def test_filter_no_match_returns_empty_list(self, client):
        r = client.get("/api/v1/packages?crop_id=no_such_crop")
        assert r.status_code == 200
        assert r.json()["packages"] == []
        assert r.json()["total"] == 0


class TestPackageDownloadEndpoint:
    def test_known_package_returns_200(self, client):
        r = client.get("/api/v1/packages/coffee/ethiopia")
        assert r.status_code == 200

    def test_unknown_crop_returns_404(self, client):
        r = client.get("/api/v1/packages/no_crop/ethiopia")
        assert r.status_code == 404

    def test_unknown_region_returns_404(self, client):
        r = client.get("/api/v1/packages/coffee/no_region")
        assert r.status_code == 404

    def test_response_content_type_is_octet_stream(self, client):
        r = client.get("/api/v1/packages/coffee/ethiopia")
        assert "application/octet-stream" in r.headers["content-type"]

    def test_response_body_is_valid_sqlite(self, client):
        r = client.get("/api/v1/packages/coffee/ethiopia")
        # SQLite files start with "SQLite format 3\x00"
        assert r.content[:16] == b"SQLite format 3\x00"

    def test_content_disposition_includes_filename(self, client):
        r = client.get("/api/v1/packages/coffee/ethiopia")
        assert "coffee_ethiopia.mbtiles" in r.headers.get("content-disposition", "")
