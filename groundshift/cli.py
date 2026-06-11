import argparse
import math
from datetime import datetime
from pathlib import Path

import numpy as np

from groundshift.core.calibration.anchor_loader import load_anchors_from_profile
from groundshift.core.calibration.anchor_scorer import score_anchors
from groundshift.core.envelope.cmip6_source import CMIP6Source
from groundshift.core.envelope.era5_source import ERA5Source
from groundshift.core.envelope.worldclim_source import WorldClimSource
from groundshift.core.envelope.yaml_loader import load_profile_from_yaml
from groundshift.core.imagery.sentinel2_source import Sentinel2Source
from groundshift.core.phases.describe import DescribePhaseRunner
from groundshift.core.phases.predict import PredictPhaseRunner
from groundshift.models.time_range import TimeRange
from groundshift.plugins.registry import PluginRegistry
from groundshift.regions.resolver import UnknownRegionError, resolve_region

_WORLDCLIM_DIR = Path(__file__).parents[1] / "data" / "worldclim" / "10m"
_ERA5_DIR = Path(__file__).parents[1] / "data" / "era5"
_SENTINEL2_DIR = Path(__file__).parents[1] / "data" / "sentinel2"
_CMIP6_DIR = Path(__file__).parents[1] / "data" / "cmip6"

_WORLDCLIM_TIME_RANGE = TimeRange(start=datetime(1970, 1, 1), end=datetime(2000, 12, 31))
_ERA5_TIME_RANGE = TimeRange(start=datetime(2015, 1, 1), end=datetime(2024, 12, 31))
_CMIP6_TIME_RANGE = TimeRange(start=datetime(2015, 1, 1), end=datetime(2100, 12, 31))

_CMIP6_SCENARIOS = ["ssp245", "ssp585"]
_CMIP6_HORIZONS = [2040, 2060, 2100]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="groundshift",
        description="Crop climate suitability analysis.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run a suitability analysis.")
    run.add_argument("--crop", required=True, help="Crop profile id (e.g. coffee)")
    run.add_argument("--region", required=True, help="Named region (e.g. ethiopia)")
    run.add_argument(
        "--phase",
        required=True,
        choices=["describe", "predict"],
        help="Pipeline phase to execute.",
    )
    run.add_argument(
        "--source",
        default="worldclim",
        choices=["worldclim", "era5"],
        help="Climate data source (default: worldclim).",
    )
    run.add_argument(
        "--imagery",
        default=None,
        choices=["sentinel2"],
        help="Imagery source for observed vegetation divergence (optional).",
    )
    return parser


def run_describe(args: argparse.Namespace) -> None:
    try:
        region = resolve_region(args.region)
    except UnknownRegionError:
        raise SystemExit(
            f"Unknown region '{args.region}'. "
            "Check groundshift/regions/resolver.py for available regions."
        )

    profile_path = Path(__file__).parents[1] / "crop_profiles" / f"{args.crop}.yaml"
    if not profile_path.exists():
        raise SystemExit(f"Crop profile not found: {profile_path}")

    profile = load_profile_from_yaml(profile_path)
    if args.source == "era5":
        source = ERA5Source(_ERA5_DIR)
        time_range = _ERA5_TIME_RANGE
    else:
        source = WorldClimSource(_WORLDCLIM_DIR)
        time_range = _WORLDCLIM_TIME_RANGE
    imagery_source = None
    if args.imagery == "sentinel2":
        imagery_source = Sentinel2Source(_SENTINEL2_DIR)
    runner = DescribePhaseRunner(source, PluginRegistry(), imagery_source=imagery_source)
    result = runner.run(profile, region, time_range)

    score = result.suitability.score.values
    finite = score[~np.isnan(score)]
    viable = finite[finite > 0]

    print("Groundshift — Describe phase")
    print(f"  crop:    {args.crop}")
    print(f"  region:  {args.region}")
    print(f"  cells:   {len(finite)} scored, {len(viable)} viable (score > 0)")
    print(f"  score:   min={finite.min():.3f}  mean={finite.mean():.3f}  max={finite.max():.3f}")

    if result.divergence is not None:
        div = result.divergence.surface.values
        finite_div = div[~np.isnan(div)]
        if len(finite_div) > 0:
            print(
                f"  divergence (climate − observed):  "
                f"min={finite_div.min():.3f}  mean={finite_div.mean():.3f}  "
                f"max={finite_div.max():.3f}"
            )

    anchors = load_anchors_from_profile(profile)
    if anchors:
        anchor_scores = score_anchors(result.suitability, anchors)
        print()
        print("  calibration anchors:")
        for a in anchor_scores:
            score_str = f"{a.score:.3f}" if not math.isnan(a.score) else "n/a (outside region)"
            alert_str = "  *** ALERT ***" if a.alert_triggered else ""
            if a.expected_min is not None:
                threshold_str = f"  (expected >= {a.expected_min:.2f})"
            else:
                threshold_str = "  (stress reference — no floor)"
            print(f"    [{a.anchor.role}] {a.anchor.name}: {score_str}{threshold_str}{alert_str}")


def run_predict(args: argparse.Namespace) -> None:
    try:
        region = resolve_region(args.region)
    except UnknownRegionError:
        raise SystemExit(
            f"Unknown region '{args.region}'. "
            "Check groundshift/regions/resolver.py for available regions."
        )

    profile_path = Path(__file__).parents[1] / "crop_profiles" / f"{args.crop}.yaml"
    if not profile_path.exists():
        raise SystemExit(f"Crop profile not found: {profile_path}")

    profile = load_profile_from_yaml(profile_path)
    source = CMIP6Source(_CMIP6_DIR)
    runner = PredictPhaseRunner(
        source, PluginRegistry(), scenarios=_CMIP6_SCENARIOS, horizons=_CMIP6_HORIZONS
    )

    try:
        result = runner.run(profile, region, _CMIP6_TIME_RANGE)
    except FileNotFoundError as exc:
        raise SystemExit(
            f"CMIP6 data not found: {exc}\nRun: python scripts/ingest/download_cmip6.py"
        )

    print("Groundshift — Predict phase")
    print(f"  crop:    {args.crop}")
    print(f"  region:  {args.region}")
    print()

    for proj in result.projections:
        score = proj.suitability.score.values
        finite = score[~np.isnan(score)]
        viable = finite[finite > 0]
        label = f"[{proj.scenario} / {proj.horizon_year}]"
        print(
            f"  {label:<18}  "
            f"min={finite.min():.3f}  mean={finite.mean():.3f}  max={finite.max():.3f}  "
            f"viable={len(viable)} cells"
        )


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    if args.command == "run":
        if args.phase == "predict":
            run_predict(args)
        else:
            run_describe(args)
