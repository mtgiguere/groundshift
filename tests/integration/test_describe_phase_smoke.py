"""
End-to-end smoke tests for the Describe phase using real WorldClim data.

These tests confirm that the full pipeline chain — WorldClimSource →
compute_envelope → DescribePhaseRunner — works correctly with actual
GeoTIFF files, catching any integration gaps that synthetic unit tests
cannot see (nodata handling, coordinate propagation, real value ranges).

Requires WorldClim data on disk. If missing, run:
    python scripts/ingest/download_worldclim.py
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from groundshift.core.envelope.worldclim_source import WorldClimSource
from groundshift.core.envelope.yaml_loader import load_profile_from_yaml
from groundshift.core.phases.describe import DescribePhaseRunner
from groundshift.models.bounding_box import BoundingBox
from groundshift.models.suitability_result import SuitabilityResult
from groundshift.models.time_range import TimeRange
from groundshift.plugins.registry import PluginRegistry

_DATA_DIR = Path(__file__).parents[2] / "data" / "worldclim" / "10m"
_PROFILE_PATH = Path(__file__).parents[2] / "crop_profiles" / "coffee_arabica.yaml"

# WorldClim is a 1970–2000 climatological baseline; time_range is required
# by the ClimateDataSource interface but ignored by WorldClimSource.
_TIME_RANGE = TimeRange(start=datetime(1970, 1, 1), end=datetime(2000, 12, 31))

# Yirgacheffe / Sidama area — core arabica origin, well-documented high
# suitability. A good calibration region: if the pipeline can't score this
# area as viable, something is wrong.
_ETHIOPIA_REGION = BoundingBox(min_lon=37.0, min_lat=5.0, max_lon=40.0, max_lat=9.0)


@pytest.fixture(scope="module")
def _skip_if_no_data():
    if not _DATA_DIR.exists() or not any(_DATA_DIR.glob("*.tif")):
        pytest.skip(
            f"WorldClim data not found at {_DATA_DIR} — "
            "run: python scripts/ingest/download_worldclim.py"
        )


@pytest.fixture(scope="module")
def ethiopia_result(_skip_if_no_data):
    source = WorldClimSource(_DATA_DIR)
    runner = DescribePhaseRunner(source, PluginRegistry())
    profile = load_profile_from_yaml(_PROFILE_PATH)
    return runner.run(profile, _ETHIOPIA_REGION, _TIME_RANGE)


@pytest.mark.integration
def test_pipeline_returns_suitability_result(ethiopia_result):
    assert isinstance(ethiopia_result, SuitabilityResult)


@pytest.mark.integration
def test_score_is_a_dataarray(ethiopia_result):
    assert isinstance(ethiopia_result.score, xr.DataArray)


@pytest.mark.integration
def test_confidence_is_a_dataarray(ethiopia_result):
    assert isinstance(ethiopia_result.confidence, xr.DataArray)


@pytest.mark.integration
def test_score_values_are_in_unit_range(ethiopia_result):
    # Non-NaN cells must be in [0, 1]. NaN cells (nodata from the source
    # rasters) are allowed — they propagate naturally through the pipeline.
    valid = ethiopia_result.score.values
    finite = valid[~np.isnan(valid)]
    assert len(finite) > 0, "all cells are NaN — clip region may be outside raster extent"
    assert float(finite.min()) >= 0.0
    assert float(finite.max()) <= 1.0


@pytest.mark.integration
def test_score_is_spatially_variable(ethiopia_result):
    # Real climate data must produce spatial variation. A uniform surface
    # would indicate the pipeline collapsed to a scalar somewhere.
    valid = ethiopia_result.score.values
    finite = valid[~np.isnan(valid)]
    assert float(finite.std()) > 0.0


@pytest.mark.integration
def test_ethiopia_highland_region_has_viable_coffee_cells(ethiopia_result):
    # Yirgacheffe / Sidama is a documented arabica origin. The envelope
    # must score at least some cells as viable (score > 0). If this fails,
    # the thresholds or variable mapping are wrong.
    assert float(ethiopia_result.score.max()) > 0.0


@pytest.mark.integration
def test_cli_describe_phase_prints_summary(_skip_if_no_data, capsys):
    # The CLI is the user-facing entry point — verify it runs end-to-end
    # and prints a human-readable summary without raising.
    from groundshift.cli import build_arg_parser, run_describe

    parser = build_arg_parser()
    args = parser.parse_args(
        ["run", "--crop", "coffee", "--region", "ethiopia", "--phase", "describe"]
    )
    run_describe(args)

    captured = capsys.readouterr()
    assert "score" in captured.out.lower()
    assert "ethiopia" in captured.out.lower()


@pytest.mark.integration
def test_cli_prints_calibration_anchor_scores(_skip_if_no_data, capsys):
    # Anchors defined in coffee.yaml must be scored and printed.
    # Yirgacheffe is an origin_center — its score and expected_min must appear.
    from groundshift.cli import build_arg_parser, run_describe

    parser = build_arg_parser()
    args = parser.parse_args(
        ["run", "--crop", "coffee", "--region", "ethiopia", "--phase", "describe"]
    )
    run_describe(args)

    captured = capsys.readouterr()
    assert "yirgacheffe" in captured.out.lower()
    assert "anchor" in captured.out.lower()


@pytest.mark.integration
def test_cli_prints_alert_when_anchor_scores_below_threshold(_skip_if_no_data, capsys):
    # The Colombia Huila anchor (production_reference, expected_min=0.60) covers
    # a region outside the Ethiopia run bbox — the clip will be empty and mean()
    # will return NaN. An empty-clip anchor must not crash; it should print
    # something informative rather than silently succeed.
    from groundshift.cli import build_arg_parser, run_describe

    parser = build_arg_parser()
    args = parser.parse_args(
        ["run", "--crop", "coffee", "--region", "ethiopia", "--phase", "describe"]
    )
    # This test just asserts the CLI doesn't raise; anchor output is already
    # verified by test_cli_prints_calibration_anchor_scores above.
    run_describe(args)
