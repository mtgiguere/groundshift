import pytest

from groundshift.cli import build_arg_parser


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
