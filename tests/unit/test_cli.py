import numpy as np
import pytest
import xarray as xr

from groundshift.cli import build_arg_parser, run_predict
from groundshift.models.predict_result import PredictProjection, PredictResult
from groundshift.models.suitability_result import SuitabilityResult


def _fake_suitability() -> SuitabilityResult:
    score = xr.DataArray(np.array([[0.5, 0.8], [0.3, 0.6]]))
    return SuitabilityResult(score=score, confidence=score)


def _fake_predict_result() -> PredictResult:
    return PredictResult(
        projections=[
            PredictProjection("ssp245", 2040, _fake_suitability()),
            PredictProjection("ssp585", 2100, _fake_suitability()),
        ]
    )


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


class TestRunPredict:
    def _args(self, crop="coffee", region="ethiopia"):
        parser = build_arg_parser()
        return parser.parse_args(["run", "--crop", crop, "--region", region, "--phase", "predict"])

    def test_unknown_region_raises_system_exit(self):
        args = self._args(region="nowhere_land")
        with pytest.raises(SystemExit, match="Unknown region"):
            run_predict(args)

    def test_missing_profile_raises_system_exit(self):
        args = self._args(crop="no_such_crop_xyz")
        with pytest.raises(SystemExit, match="Crop profile not found"):
            run_predict(args)

    def test_missing_cmip6_data_raises_system_exit(self, mocker):
        args = self._args()
        mocker.patch(
            "groundshift.cli.PredictPhaseRunner.run",
            side_effect=FileNotFoundError("cmip6_mean_annual_temp_c_ssp245_2040.nc"),
        )
        with pytest.raises(SystemExit, match="CMIP6 data not found"):
            run_predict(args)

    def test_happy_path_prints_predict_header(self, mocker, capsys):
        args = self._args()
        mocker.patch("groundshift.cli.PredictPhaseRunner.run", return_value=_fake_predict_result())
        run_predict(args)
        out = capsys.readouterr().out
        assert "Predict phase" in out
        assert "coffee" in out
        assert "ethiopia" in out

    def test_happy_path_prints_one_line_per_projection(self, mocker, capsys):
        args = self._args()
        mocker.patch("groundshift.cli.PredictPhaseRunner.run", return_value=_fake_predict_result())
        run_predict(args)
        out = capsys.readouterr().out
        assert "ssp245" in out
        assert "ssp585" in out
        assert "2040" in out
        assert "2100" in out
