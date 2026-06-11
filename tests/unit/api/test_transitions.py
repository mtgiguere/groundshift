import pytest
import yaml
from fastapi.testclient import TestClient


def _write_profile(profiles_dir, crop_id, name, thresholds):
    data = {
        "crop_id": crop_id,
        "name": name,
        "climate_envelope": {"thresholds": thresholds},
    }
    (profiles_dir / f"{crop_id}.yaml").write_text(yaml.dump(data))


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    from groundshift.api.app import create_app

    profiles_dir = tmp_path_factory.mktemp("profiles")

    # coffee and tea share the same temperature variable → overlap > 0
    coffee_thresholds = {
        "temperature_mean": {
            "viable_min": 15,
            "optimal_min": 18,
            "optimal_max": 24,
            "viable_max": 28,
        }
    }
    tea_thresholds = {
        "temperature_mean": {
            "viable_min": 12,
            "optimal_min": 16,
            "optimal_max": 22,
            "viable_max": 26,
        }
    }
    wheat_thresholds = {
        "temperature_mean": {
            "viable_min": 5,
            "optimal_min": 10,
            "optimal_max": 15,
            "viable_max": 20,
        }
    }
    _write_profile(profiles_dir, "coffee", "Coffee", coffee_thresholds)
    _write_profile(profiles_dir, "tea", "Tea", tea_thresholds)
    _write_profile(profiles_dir, "wheat", "Wheat", wheat_thresholds)

    return TestClient(create_app(profiles_dir=profiles_dir))


class TestTransitionsEndpoint:
    def test_known_crop_returns_200(self, client):
        r = client.get("/api/v1/crops/coffee/transitions")
        assert r.status_code == 200

    def test_unknown_crop_returns_404(self, client):
        r = client.get("/api/v1/crops/no_such_crop/transitions")
        assert r.status_code == 404

    def test_response_has_crop_id(self, client):
        r = client.get("/api/v1/crops/coffee/transitions")
        assert r.json()["crop_id"] == "coffee"

    def test_response_has_suggestions_list(self, client):
        r = client.get("/api/v1/crops/coffee/transitions")
        assert isinstance(r.json()["suggestions"], list)

    def test_suggestions_exclude_current_crop(self, client):
        r = client.get("/api/v1/crops/coffee/transitions")
        ids = [s["crop_id"] for s in r.json()["suggestions"]]
        assert "coffee" not in ids

    def test_suggestions_count_is_other_crops(self, client):
        r = client.get("/api/v1/crops/coffee/transitions")
        # 3 profiles total, minus the current crop = 2 suggestions
        assert len(r.json()["suggestions"]) == 2

    def test_suggestion_has_crop_id(self, client):
        r = client.get("/api/v1/crops/coffee/transitions")
        assert "crop_id" in r.json()["suggestions"][0]

    def test_suggestion_has_crop_name(self, client):
        r = client.get("/api/v1/crops/coffee/transitions")
        assert "crop_name" in r.json()["suggestions"][0]

    def test_suggestion_has_overlap_score(self, client):
        r = client.get("/api/v1/crops/coffee/transitions")
        assert "overlap_score" in r.json()["suggestions"][0]

    def test_overlap_score_is_float_between_0_and_1(self, client):
        r = client.get("/api/v1/crops/coffee/transitions")
        for s in r.json()["suggestions"]:
            assert 0.0 <= s["overlap_score"] <= 1.0

    def test_suggestions_sorted_descending_by_overlap(self, client):
        r = client.get("/api/v1/crops/coffee/transitions")
        scores = [s["overlap_score"] for s in r.json()["suggestions"]]
        assert scores == sorted(scores, reverse=True)

    def test_tea_scores_higher_than_wheat_for_coffee(self, client):
        r = client.get("/api/v1/crops/coffee/transitions")
        by_id = {s["crop_id"]: s["overlap_score"] for s in r.json()["suggestions"]}
        # tea shares more of coffee's temperature range than wheat does
        assert by_id["tea"] > by_id["wheat"]
