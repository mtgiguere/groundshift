"""Unit tests for GET /api/v1/plugins."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def plugin_data_dir(tmp_path):
    return tmp_path


@pytest.fixture
def client(plugin_data_dir):
    from groundshift.api.app import create_app

    return TestClient(create_app(plugin_data_dir=plugin_data_dir))


class TestPluginsList:
    def test_returns_200(self, client):
        r = client.get("/api/v1/plugins")
        assert r.status_code == 200

    def test_response_has_plugins_key(self, client):
        r = client.get("/api/v1/plugins")
        assert "plugins" in r.json()

    def test_total_is_six(self, client):
        r = client.get("/api/v1/plugins")
        assert r.json()["total"] == 6

    def test_total_matches_list_length(self, client):
        r = client.get("/api/v1/plugins")
        data = r.json()
        assert data["total"] == len(data["plugins"])

    def test_all_known_plugin_ids_present(self, client):
        ids = {p["plugin_id"] for p in client.get("/api/v1/plugins").json()["plugins"]}
        assert ids == {
            "frost_risk",
            "drought_stress",
            "heat_stress",
            "groundwater",
            "pest_disease",
            "cooperative_infra",
        }

    def test_each_plugin_has_required_fields(self, client):
        for plugin in client.get("/api/v1/plugins").json()["plugins"]:
            for field in ("plugin_id", "name", "description", "threat_tier", "version", "status"):
                assert field in plugin

    def test_status_unavailable_when_no_data(self, client):
        for plugin in client.get("/api/v1/plugins").json()["plugins"]:
            assert plugin["status"] == "unavailable"


class TestPluginAvailability:
    def test_frost_risk_available_when_file_present(self, tmp_path):
        from groundshift.api.app import create_app

        (tmp_path / "frost_risk_min_temp_ssp245_2040.nc").touch()
        c = TestClient(create_app(plugin_data_dir=tmp_path))
        plugins = {p["plugin_id"]: p for p in c.get("/api/v1/plugins").json()["plugins"]}
        assert plugins["frost_risk"]["status"] == "available"
        assert plugins["drought_stress"]["status"] == "unavailable"
        assert plugins["heat_stress"]["status"] == "unavailable"

    def test_drought_stress_available_when_file_present(self, tmp_path):
        from groundshift.api.app import create_app

        (tmp_path / "drought_stress_precip_ssp245_2040.nc").touch()
        c = TestClient(create_app(plugin_data_dir=tmp_path))
        plugins = {p["plugin_id"]: p for p in c.get("/api/v1/plugins").json()["plugins"]}
        assert plugins["drought_stress"]["status"] == "available"
        assert plugins["frost_risk"]["status"] == "unavailable"
        assert plugins["heat_stress"]["status"] == "unavailable"

    def test_heat_stress_available_when_file_present(self, tmp_path):
        from groundshift.api.app import create_app

        (tmp_path / "heat_stress_mean_temp_ssp245_2040.nc").touch()
        c = TestClient(create_app(plugin_data_dir=tmp_path))
        plugins = {p["plugin_id"]: p for p in c.get("/api/v1/plugins").json()["plugins"]}
        assert plugins["heat_stress"]["status"] == "available"
        assert plugins["frost_risk"]["status"] == "unavailable"
        assert plugins["drought_stress"]["status"] == "unavailable"

    def test_groundwater_available_when_file_present(self, tmp_path):
        from groundshift.api.app import create_app

        (tmp_path / "groundwater_tws_baseline.nc").touch()
        c = TestClient(create_app(plugin_data_dir=tmp_path))
        plugins = {p["plugin_id"]: p for p in c.get("/api/v1/plugins").json()["plugins"]}
        assert plugins["groundwater"]["status"] == "available"
        assert plugins["frost_risk"]["status"] == "unavailable"

    def test_pest_disease_available_when_file_present(self, tmp_path):
        from groundshift.api.app import create_app

        (tmp_path / "pest_disease_clr_ssp245_2040.nc").touch()
        c = TestClient(create_app(plugin_data_dir=tmp_path))
        plugins = {p["plugin_id"]: p for p in c.get("/api/v1/plugins").json()["plugins"]}
        assert plugins["pest_disease"]["status"] == "available"
        assert plugins["frost_risk"]["status"] == "unavailable"

    def test_cooperative_infra_available_when_file_present(self, tmp_path):
        from groundshift.api.app import create_app

        (tmp_path / "cooperative_infra_access.nc").touch()
        c = TestClient(create_app(plugin_data_dir=tmp_path))
        plugins = {p["plugin_id"]: p for p in c.get("/api/v1/plugins").json()["plugins"]}
        assert plugins["cooperative_infra"]["status"] == "available"
        assert plugins["frost_risk"]["status"] == "unavailable"

    def test_all_available_when_all_files_present(self, tmp_path):
        from groundshift.api.app import create_app

        (tmp_path / "frost_risk_min_temp_ssp245_2040.nc").touch()
        (tmp_path / "drought_stress_precip_ssp245_2040.nc").touch()
        (tmp_path / "heat_stress_mean_temp_ssp245_2040.nc").touch()
        (tmp_path / "groundwater_tws_baseline.nc").touch()
        (tmp_path / "pest_disease_clr_ssp245_2040.nc").touch()
        (tmp_path / "cooperative_infra_access.nc").touch()
        c = TestClient(create_app(plugin_data_dir=tmp_path))
        statuses = {p["plugin_id"]: p["status"] for p in c.get("/api/v1/plugins").json()["plugins"]}
        assert all(s == "available" for s in statuses.values())
