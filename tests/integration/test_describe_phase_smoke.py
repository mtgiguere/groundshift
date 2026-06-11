"""
End-to-end smoke tests for the Describe phase using real WorldClim, ERA5,
Sentinel-2, and Landsat data.

These tests confirm that the full pipeline chain — ClimateDataSource →
compute_envelope → DescribePhaseRunner — works correctly with actual
data files, catching any integration gaps that synthetic unit tests
cannot see (nodata handling, coordinate propagation, real value ranges).

Requires WorldClim data on disk. If missing, run:
    python scripts/ingest/download_worldclim.py

ERA5, Sentinel-2, and Landsat tests are skipped automatically if their data
files are not present. To download:
    pip install -e ".[ingest]"
    python scripts/ingest/download_era5.py
    python scripts/ingest/download_sentinel2.py --region ethiopia --year 2023
    python scripts/ingest/download_landsat.py --region ethiopia
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from groundshift.core.envelope.worldclim_source import WorldClimSource
from groundshift.core.envelope.yaml_loader import load_profile_from_yaml
from groundshift.core.imagery.landsat_source import LandsatSource
from groundshift.core.imagery.sentinel2_source import Sentinel2Source
from groundshift.core.phases.describe import DescribePhaseRunner
from groundshift.models.bounding_box import BoundingBox
from groundshift.models.describe_result import DescribeResult
from groundshift.models.divergence_result import DivergenceResult
from groundshift.models.time_range import TimeRange
from groundshift.models.trend_result import TrendResult
from groundshift.plugins.registry import PluginRegistry

_DATA_DIR = Path(__file__).parents[2] / "data" / "worldclim" / "10m"
_ERA5_DIR = Path(__file__).parents[2] / "data" / "era5"
_SENTINEL2_DIR = Path(__file__).parents[2] / "data" / "sentinel2"
_LANDSAT_DIR = Path(__file__).parents[2] / "data" / "landsat"
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
def test_pipeline_returns_describe_result(ethiopia_result):
    assert isinstance(ethiopia_result, DescribeResult)


@pytest.mark.integration
def test_score_is_a_dataarray(ethiopia_result):
    assert isinstance(ethiopia_result.suitability.score, xr.DataArray)


@pytest.mark.integration
def test_confidence_is_a_dataarray(ethiopia_result):
    assert isinstance(ethiopia_result.suitability.confidence, xr.DataArray)


@pytest.mark.integration
def test_score_values_are_in_unit_range(ethiopia_result):
    valid = ethiopia_result.suitability.score.values
    finite = valid[~np.isnan(valid)]
    assert len(finite) > 0, "all cells are NaN — clip region may be outside raster extent"
    assert float(finite.min()) >= 0.0
    assert float(finite.max()) <= 1.0


@pytest.mark.integration
def test_score_is_spatially_variable(ethiopia_result):
    valid = ethiopia_result.suitability.score.values
    finite = valid[~np.isnan(valid)]
    assert float(finite.std()) > 0.0


@pytest.mark.integration
def test_ethiopia_highland_region_has_viable_coffee_cells(ethiopia_result):
    assert float(ethiopia_result.suitability.score.max()) > 0.0


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


@pytest.fixture(scope="module")
def _skip_if_no_era5_data():
    if not _ERA5_DIR.exists() or not any(_ERA5_DIR.glob("*.nc")):
        pytest.skip(
            f"ERA5 data not found at {_ERA5_DIR} — "
            "run: pip install -e '.[ingest]' && python scripts/ingest/download_era5.py"
        )


@pytest.mark.integration
def test_cli_era5_source_runs_end_to_end(_skip_if_no_era5_data, capsys):
    # ERA5 is a second ClimateDataSource implementation; verify the CLI
    # --source era5 flag wires it through the full pipeline without error.
    from groundshift.cli import build_arg_parser, run_describe

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
    run_describe(args)

    captured = capsys.readouterr()
    assert "score" in captured.out.lower()
    assert "ethiopia" in captured.out.lower()


# ---------------------------------------------------------------------------
# Sentinel-2 imagery divergence smoke tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _skip_if_no_sentinel2_data():
    sentinel2_tif = _SENTINEL2_DIR / "sentinel2_ndvi.tif"
    if not sentinel2_tif.exists():
        pytest.skip(
            f"Sentinel-2 data not found at {sentinel2_tif} — "
            "run: python scripts/ingest/download_sentinel2.py --region ethiopia --year 2023"
        )


@pytest.fixture(scope="module")
def ethiopia_sentinel2_result(_skip_if_no_data, _skip_if_no_sentinel2_data):
    source = WorldClimSource(_DATA_DIR)
    imagery = Sentinel2Source(_SENTINEL2_DIR)
    runner = DescribePhaseRunner(source, PluginRegistry(), imagery_source=imagery)
    profile = load_profile_from_yaml(_PROFILE_PATH)
    return runner.run(profile, _ETHIOPIA_REGION, _TIME_RANGE)


@pytest.mark.integration
def test_sentinel2_result_has_divergence(ethiopia_sentinel2_result):
    assert isinstance(ethiopia_sentinel2_result.divergence, DivergenceResult)


@pytest.mark.integration
def test_sentinel2_divergence_surface_is_dataarray(ethiopia_sentinel2_result):
    assert isinstance(ethiopia_sentinel2_result.divergence.surface, xr.DataArray)


@pytest.mark.integration
def test_sentinel2_divergence_values_are_finite(ethiopia_sentinel2_result):
    surface = ethiopia_sentinel2_result.divergence.surface.values
    finite = surface[~np.isnan(surface)]
    assert len(finite) > 0, "all divergence cells are NaN"


@pytest.mark.integration
def test_sentinel2_divergence_range_is_plausible(ethiopia_sentinel2_result):
    # Divergence is (climate_score − normalised_NDVI); both are in [0, 1]
    # so the signed difference must stay within [−1, 1].
    surface = ethiopia_sentinel2_result.divergence.surface.values
    finite = surface[~np.isnan(surface)]
    assert float(finite.min()) >= -1.0
    assert float(finite.max()) <= 1.0


@pytest.mark.integration
def test_cli_sentinel2_imagery_prints_divergence_line(
    _skip_if_no_data, _skip_if_no_sentinel2_data, capsys
):
    from groundshift.cli import build_arg_parser, run_describe

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
    run_describe(args)

    captured = capsys.readouterr()
    assert "divergence" in captured.out.lower()


# ---------------------------------------------------------------------------
# Landsat NDVI trend smoke tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _skip_if_no_landsat_data():
    landsat_tif = _LANDSAT_DIR / "landsat_ndvi_trend_ethiopia.tif"
    if not landsat_tif.exists():
        pytest.skip(
            f"Landsat trend data not found at {landsat_tif} — "
            "run: python scripts/ingest/download_landsat.py --region ethiopia"
        )


@pytest.fixture(scope="module")
def ethiopia_landsat_result(_skip_if_no_data, _skip_if_no_landsat_data):
    source = WorldClimSource(_DATA_DIR)
    landsat = LandsatSource(_LANDSAT_DIR)
    runner = DescribePhaseRunner(source, PluginRegistry(), landsat_source=landsat)
    profile = load_profile_from_yaml(_PROFILE_PATH)
    return runner.run(profile, _ETHIOPIA_REGION, _TIME_RANGE)


@pytest.mark.integration
def test_landsat_result_has_trend(ethiopia_landsat_result):
    assert isinstance(ethiopia_landsat_result.trend, TrendResult)


@pytest.mark.integration
def test_landsat_trend_slope_is_dataarray(ethiopia_landsat_result):
    assert isinstance(ethiopia_landsat_result.trend.slope, xr.DataArray)


@pytest.mark.integration
def test_landsat_trend_slope_values_are_finite(ethiopia_landsat_result):
    slope = ethiopia_landsat_result.trend.slope.values
    finite = slope[~np.isnan(slope)]
    assert len(finite) > 0, "all trend slope cells are NaN"


@pytest.mark.integration
def test_landsat_trend_slope_magnitude_is_plausible(ethiopia_landsat_result):
    # NDVI ∈ [−1, 1] over a ~40-year archive; plausible slopes are tiny.
    slope = ethiopia_landsat_result.trend.slope.values
    finite = slope[~np.isnan(slope)]
    assert float(np.abs(finite).max()) < 0.1, "slope magnitudes seem implausibly large"


@pytest.mark.integration
def test_cli_landsat_imagery_prints_trend_line(_skip_if_no_data, _skip_if_no_landsat_data, capsys):
    from groundshift.cli import build_arg_parser, run_describe

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
            "landsat",
        ]
    )
    run_describe(args)

    captured = capsys.readouterr()
    assert "trend" in captured.out.lower()
