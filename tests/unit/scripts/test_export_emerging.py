import json
from pathlib import Path

import numpy as np
import xarray as xr

from groundshift.models.opportunity_zone import OpportunityZone, OpportunityZoneResult
from scripts.export_emerging import _build_result_data, _output_path


def _fake_opportunity() -> OpportunityZoneResult:
    mask_a = xr.DataArray(np.array([[True, False], [True, True]]))  # 3 cells
    mask_b = xr.DataArray(np.array([[False, False], [True, False]]))  # 1 cell
    return OpportunityZoneResult(
        zones=[
            OpportunityZone("ssp245", 2040, mask_a, "low"),
            OpportunityZone("ssp585", 2100, mask_b, "low"),
        ]
    )


class TestBuildResultData:
    def test_crop_id_matches_input(self):
        data = _build_result_data("coffee", "ethiopia", _fake_opportunity())
        assert data["crop_id"] == "coffee"

    def test_region_matches_input(self):
        data = _build_result_data("coffee", "ethiopia", _fake_opportunity())
        assert data["region"] == "ethiopia"

    def test_zones_is_list(self):
        data = _build_result_data("coffee", "ethiopia", _fake_opportunity())
        assert isinstance(data["zones"], list)

    def test_zone_count_matches_opportunity_zones(self):
        data = _build_result_data("coffee", "ethiopia", _fake_opportunity())
        assert len(data["zones"]) == 2

    def test_zone_has_required_fields(self):
        data = _build_result_data("coffee", "ethiopia", _fake_opportunity())
        zone = data["zones"][0]
        for key in ("scenario", "horizon_year", "cell_count", "confidence"):
            assert key in zone

    def test_cell_count_is_python_int(self):
        data = _build_result_data("coffee", "ethiopia", _fake_opportunity())
        assert isinstance(data["zones"][0]["cell_count"], int)

    def test_cell_count_correct_for_first_zone(self):
        data = _build_result_data("coffee", "ethiopia", _fake_opportunity())
        assert data["zones"][0]["cell_count"] == 3

    def test_cell_count_correct_for_second_zone(self):
        data = _build_result_data("coffee", "ethiopia", _fake_opportunity())
        assert data["zones"][1]["cell_count"] == 1

    def test_scenario_preserved(self):
        data = _build_result_data("coffee", "ethiopia", _fake_opportunity())
        assert data["zones"][0]["scenario"] == "ssp245"
        assert data["zones"][1]["scenario"] == "ssp585"

    def test_horizon_year_preserved(self):
        data = _build_result_data("coffee", "ethiopia", _fake_opportunity())
        assert data["zones"][0]["horizon_year"] == 2040
        assert data["zones"][1]["horizon_year"] == 2100

    def test_confidence_preserved(self):
        data = _build_result_data("coffee", "ethiopia", _fake_opportunity())
        assert data["zones"][0]["confidence"] == "low"


class TestOutputPath:
    def test_uses_crop_and_region_in_filename(self):
        path = _output_path(Path("/some/dir"), "coffee", "ethiopia")
        assert path.name == "coffee_ethiopia.json"

    def test_is_under_results_dir(self):
        path = _output_path(Path("/some/dir"), "coffee", "ethiopia")
        assert path.parent == Path("/some/dir")

    def test_json_extension(self):
        path = _output_path(Path("/some/dir"), "tea", "colombia")
        assert path.suffix == ".json"


class TestExportWritesFile:
    def test_file_is_written(self, tmp_path):
        from unittest.mock import patch

        from groundshift.models.describe_result import DescribeResult
        from groundshift.models.predict_result import PredictProjection, PredictResult
        from groundshift.models.prescribe_result import ChangeProjection, PrescribeResult
        from groundshift.models.suitability_result import SuitabilityResult
        from scripts.export_emerging import export_emerging

        score = xr.DataArray(np.array([[0.1, 0.8]]))
        suitability = SuitabilityResult(score=score, confidence=score)
        describe = DescribeResult(suitability=suitability)
        predict = PredictResult(projections=[PredictProjection("ssp245", 2040, suitability)])
        prescribe = PrescribeResult(
            change_projections=[
                ChangeProjection("ssp245", 2040, xr.DataArray(np.array([[0.2, -0.1]])))
            ]
        )

        with patch("scripts.export_emerging.DescribePhaseRunner.run", return_value=describe):
            with patch("scripts.export_emerging.PredictPhaseRunner.run", return_value=predict):
                with patch(
                    "scripts.export_emerging.PrescribePhaseRunner.run", return_value=prescribe
                ):
                    export_emerging("coffee", "ethiopia", results_dir=tmp_path)

        assert (tmp_path / "coffee_ethiopia.json").exists()

    def test_written_file_is_valid_json(self, tmp_path):
        from unittest.mock import patch

        from groundshift.models.describe_result import DescribeResult
        from groundshift.models.predict_result import PredictProjection, PredictResult
        from groundshift.models.prescribe_result import ChangeProjection, PrescribeResult
        from groundshift.models.suitability_result import SuitabilityResult
        from scripts.export_emerging import export_emerging

        score = xr.DataArray(np.array([[0.1, 0.8]]))
        suitability = SuitabilityResult(score=score, confidence=score)
        describe = DescribeResult(suitability=suitability)
        predict = PredictResult(projections=[PredictProjection("ssp245", 2040, suitability)])
        prescribe = PrescribeResult(
            change_projections=[
                ChangeProjection("ssp245", 2040, xr.DataArray(np.array([[0.2, -0.1]])))
            ]
        )

        with patch("scripts.export_emerging.DescribePhaseRunner.run", return_value=describe):
            with patch("scripts.export_emerging.PredictPhaseRunner.run", return_value=predict):
                with patch(
                    "scripts.export_emerging.PrescribePhaseRunner.run", return_value=prescribe
                ):
                    export_emerging("coffee", "ethiopia", results_dir=tmp_path)

        data = json.loads((tmp_path / "coffee_ethiopia.json").read_text())
        assert data["crop_id"] == "coffee"
        assert data["region"] == "ethiopia"
        assert isinstance(data["zones"], list)
