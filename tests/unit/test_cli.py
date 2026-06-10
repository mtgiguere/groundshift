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


def test_run_invalid_phase_exits_with_error():
    # Only 'describe' is implemented; other phases are not valid yet.
    parser = build_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "--crop", "coffee", "--region", "ethiopia", "--phase", "invalid"])
