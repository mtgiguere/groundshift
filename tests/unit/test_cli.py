from unittest.mock import patch

import numpy as np
import pytest
import xarray as xr

from groundshift.cli import build_arg_parser, run_describe, run_predict, run_prescribe
from groundshift.models.describe_result import DescribeResult
from groundshift.models.divergence_result import DivergenceResult
from groundshift.models.opportunity_zone import OpportunityZone, OpportunityZoneResult
from groundshift.models.predict_result import PredictProjection, PredictResult
from groundshift.models.prescribe_result import ChangeProjection, PrescribeResult
from groundshift.models.suitability_result import SuitabilityResult

# ---------------------------------------------------------------------------
# Shared fake data helpers
# ---------------------------------------------------------------------------


def _fake_suitability() -> SuitabilityResult:
    score = xr.DataArray(np.array([[0.5, 0.8], [0.3, 0.6]]))
    return SuitabilityResult(score=score, confidence=score)


def _fake_describe_result(with_divergence: bool = False) -> DescribeResult:
    suitability = _fake_suitability()
    divergence = None
    if with_divergence:
        surface = xr.DataArray(np.array([[0.1, -0.2], [0.3, -0.1]]))
        divergence = DivergenceResult(surface=surface)
    return DescribeResult(suitability=suitability, divergence=divergence)


def _fake_predict_result() -> PredictResult:
    return PredictResult(
        projections=[
            PredictProjection("ssp245", 2040, _fake_suitability()),
            PredictProjection("ssp585", 2100, _fake_suitability()),
        ]
    )


def _fake_prescribe_result() -> PrescribeResult:
    delta = xr.DataArray(np.array([[0.1, -0.2], [0.3, -0.1]]))
    return PrescribeResult(
        change_projections=[
            ChangeProjection("ssp245", 2040, delta),
            ChangeProjection("ssp585", 2100, delta * -1),
        ]
    )


def _fake_opportunity_zone_result() -> OpportunityZoneResult:
    mask = xr.DataArray(np.array([[True, False], [True, False]]))
    return OpportunityZoneResult(
        zones=[
            OpportunityZone("ssp245", 2040, mask, "low"),
            OpportunityZone("ssp585", 2100, mask, "low"),
        ]
    )


# ---------------------------------------------------------------------------
# Argument parser tests
# ---------------------------------------------------------------------------


def test_run_parses_required_arguments():
    parser = build_arg_parser()
    args = parser.parse_args(
        ["run", "--crop", "coffee", "--region", "ethiopia", "--phase", "describe"]
    )
    assert args.crop == "coffee"
    assert args.region == "ethiopia"
    assert args.phase == "describe"


def test_run_missing_crop_exits_with_error():
    parser = build_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "--region", "ethiopia", "--phase", "describe"])


def test_run_missing_region_exits_with_error():
    parser = build_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "--crop", "coffee", "--phase", "describe"])


def test_run_missing_phase_exits_with_error():
    parser = build_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "--crop", "coffee", "--region", "ethiopia"])


def test_predict_phase_is_accepted():
    parser = build_arg_parser()
    args = parser.parse_args(
        ["run", "--crop", "coffee", "--region", "ethiopia", "--phase", "predict"]
    )
    assert args.phase == "predict"


def test_prescribe_phase_is_accepted():
    parser = build_arg_parser()
    args = parser.parse_args(
        ["run", "--crop", "coffee", "--region", "ethiopia", "--phase", "prescribe"]
    )
    assert args.phase == "prescribe"


def test_run_invalid_phase_exits_with_error():
    parser = build_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "--crop", "coffee", "--region", "ethiopia", "--phase", "invalid"])


def test_source_defaults_to_worldclim():
    parser = build_arg_parser()
    args = parser.parse_args(
        ["run", "--crop", "coffee", "--region", "ethiopia", "--phase", "describe"]
    )
    assert args.source == "worldclim"


def test_source_era5_is_accepted():
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "run",
            "--crop",
            "coffee",
            "--region",
            "ethiopia",
            "--phase",
            "describe",
            "--source",
            "era5",
        ]
    )
    assert args.source == "era5"


def test_source_invalid_exits_with_error():
    parser = build_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "run",
                "--crop",
                "coffee",
                "--region",
                "ethiopia",
                "--phase",
                "describe",
                "--source",
                "foobar",
            ]
        )


def test_imagery_defaults_to_none():
    parser = build_arg_parser()
    args = parser.parse_args(
        ["run", "--crop", "coffee", "--region", "ethiopia", "--phase", "describe"]
    )
    assert args.imagery is None


def test_imagery_sentinel2_is_accepted():
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "run",
            "--crop",
            "coffee",
            "--region",
            "ethiopia",
            "--phase",
            "describe",
            "--imagery",
            "sentinel2",
        ]
    )
    assert args.imagery == "sentinel2"


def test_imagery_invalid_exits_with_error():
    parser = build_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "run",
                "--crop",
                "coffee",
                "--region",
                "ethiopia",
                "--phase",
                "describe",
                "--imagery",
                "foobar",
            ]
        )


# ---------------------------------------------------------------------------
# run_describe execution tests
# ---------------------------------------------------------------------------


class TestRunDescribe:
    def _args(self, crop="coffee", region="ethiopia", source="worldclim", imagery=None):
        argv = [
            "run",
            "--crop",
            crop,
            "--region",
            region,
            "--phase",
            "describe",
            "--source",
            source,
        ]
        if imagery:
            argv += ["--imagery", imagery]
        return build_arg_parser().parse_args(argv)

    def test_unknown_region_raises_system_exit(self):
        with pytest.raises(SystemExit, match="Unknown region"):
            run_describe(self._args(region="nowhere_land"))

    def test_missing_profile_raises_system_exit(self):
        with pytest.raises(SystemExit, match="Crop profile not found"):
            run_describe(self._args(crop="no_such_crop_xyz"))

    def test_happy_path_prints_describe_header(self, capsys):
        with patch("groundshift.cli.DescribePhaseRunner.run", return_value=_fake_describe_result()):
            with patch("groundshift.cli.load_anchors_from_profile", return_value=[]):
                run_describe(self._args())
        out = capsys.readouterr().out
        assert "Describe phase" in out
        assert "coffee" in out
        assert "ethiopia" in out

    def test_happy_path_prints_score_summary(self, capsys):
        with patch("groundshift.cli.DescribePhaseRunner.run", return_value=_fake_describe_result()):
            with patch("groundshift.cli.load_anchors_from_profile", return_value=[]):
                run_describe(self._args())
        out = capsys.readouterr().out
        assert "score:" in out
        assert "min=" in out

    def test_divergence_line_printed_when_present(self, capsys):
        with patch(
            "groundshift.cli.DescribePhaseRunner.run",
            return_value=_fake_describe_result(with_divergence=True),
        ):
            with patch("groundshift.cli.load_anchors_from_profile", return_value=[]):
                run_describe(self._args())
        out = capsys.readouterr().out
        assert "divergence" in out

    def test_era5_source_accepted(self, capsys):
        with patch("groundshift.cli.DescribePhaseRunner.run", return_value=_fake_describe_result()):
            with patch("groundshift.cli.load_anchors_from_profile", return_value=[]):
                run_describe(self._args(source="era5"))
        assert "Describe phase" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# run_predict execution tests
# ---------------------------------------------------------------------------


class TestRunPredict:
    def _args(self, crop="coffee", region="ethiopia"):
        return build_arg_parser().parse_args(
            ["run", "--crop", crop, "--region", region, "--phase", "predict"]
        )

    def test_unknown_region_raises_system_exit(self):
        with pytest.raises(SystemExit, match="Unknown region"):
            run_predict(self._args(region="nowhere_land"))

    def test_missing_profile_raises_system_exit(self):
        with pytest.raises(SystemExit, match="Crop profile not found"):
            run_predict(self._args(crop="no_such_crop_xyz"))

    def test_missing_cmip6_data_raises_system_exit(self):
        with patch(
            "groundshift.cli.PredictPhaseRunner.run",
            side_effect=FileNotFoundError("cmip6_mean_annual_temp_c_ssp245_2040.nc"),
        ):
            with pytest.raises(SystemExit, match="CMIP6 data not found"):
                run_predict(self._args())

    def test_happy_path_prints_predict_header(self, capsys):
        with patch("groundshift.cli.PredictPhaseRunner.run", return_value=_fake_predict_result()):
            run_predict(self._args())
        out = capsys.readouterr().out
        assert "Predict phase" in out
        assert "coffee" in out
        assert "ethiopia" in out

    def test_happy_path_prints_one_line_per_projection(self, capsys):
        with patch("groundshift.cli.PredictPhaseRunner.run", return_value=_fake_predict_result()):
            run_predict(self._args())
        out = capsys.readouterr().out
        assert "ssp245" in out
        assert "ssp585" in out
        assert "2040" in out
        assert "2100" in out


# ---------------------------------------------------------------------------
# run_prescribe execution tests
# ---------------------------------------------------------------------------


class TestRunPrescribe:
    def _args(self, crop="coffee", region="ethiopia"):
        return build_arg_parser().parse_args(
            ["run", "--crop", crop, "--region", region, "--phase", "prescribe"]
        )

    def test_unknown_region_raises_system_exit(self):
        with pytest.raises(SystemExit, match="Unknown region"):
            run_prescribe(self._args(region="nowhere_land"))

    def test_missing_profile_raises_system_exit(self):
        with pytest.raises(SystemExit, match="Crop profile not found"):
            run_prescribe(self._args(crop="no_such_crop_xyz"))

    def test_missing_data_raises_system_exit(self):
        with patch(
            "groundshift.cli.DescribePhaseRunner.run",
            side_effect=FileNotFoundError("worldclim_mean_annual_temp_c.tif"),
        ):
            with pytest.raises(SystemExit, match="Required data not found"):
                run_prescribe(self._args())

    def test_happy_path_prints_prescribe_header(self, capsys):
        with patch("groundshift.cli.DescribePhaseRunner.run", return_value=_fake_describe_result()):
            with patch(
                "groundshift.cli.PredictPhaseRunner.run", return_value=_fake_predict_result()
            ):
                with patch(
                    "groundshift.cli.PrescribePhaseRunner.run",
                    return_value=_fake_prescribe_result(),
                ):
                    run_prescribe(self._args())
        out = capsys.readouterr().out
        assert "Prescribe phase" in out
        assert "coffee" in out
        assert "ethiopia" in out

    def test_happy_path_prints_one_line_per_change_projection(self, capsys):
        with patch("groundshift.cli.DescribePhaseRunner.run", return_value=_fake_describe_result()):
            with patch(
                "groundshift.cli.PredictPhaseRunner.run", return_value=_fake_predict_result()
            ):
                with patch(
                    "groundshift.cli.PrescribePhaseRunner.run",
                    return_value=_fake_prescribe_result(),
                ):
                    run_prescribe(self._args())
        out = capsys.readouterr().out
        assert "ssp245" in out
        assert "ssp585" in out
        assert "gaining" in out
        assert "losing" in out
        assert "mean_delta" in out

    def test_opportunity_zones_header_printed(self, capsys):
        with patch("groundshift.cli.DescribePhaseRunner.run", return_value=_fake_describe_result()):
            with patch(
                "groundshift.cli.PredictPhaseRunner.run", return_value=_fake_predict_result()
            ):
                with patch(
                    "groundshift.cli.PrescribePhaseRunner.run",
                    return_value=_fake_prescribe_result(),
                ):
                    with patch(
                        "groundshift.cli.GainZoneDetector.detect",
                        return_value=_fake_opportunity_zone_result(),
                    ):
                        run_prescribe(self._args())
        assert "opportunity" in capsys.readouterr().out.lower()

    def test_opportunity_zones_cell_count_printed(self, capsys):
        with patch("groundshift.cli.DescribePhaseRunner.run", return_value=_fake_describe_result()):
            with patch(
                "groundshift.cli.PredictPhaseRunner.run", return_value=_fake_predict_result()
            ):
                with patch(
                    "groundshift.cli.PrescribePhaseRunner.run",
                    return_value=_fake_prescribe_result(),
                ):
                    with patch(
                        "groundshift.cli.GainZoneDetector.detect",
                        return_value=_fake_opportunity_zone_result(),
                    ):
                        run_prescribe(self._args())
        out = capsys.readouterr().out
        assert "cells" in out
