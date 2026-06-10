import argparse
import math
from datetime import datetime
from pathlib import Path

import numpy as np

from groundshift.core.calibration.anchor_loader import load_anchors_from_profile
from groundshift.core.calibration.anchor_scorer import score_anchors
from groundshift.core.envelope.era5_source import ERA5Source
from groundshift.core.envelope.worldclim_source import WorldClimSource
from groundshift.core.envelope.yaml_loader import load_profile_from_yaml
from groundshift.core.phases.describe import DescribePhaseRunner
from groundshift.models.time_range import TimeRange
from groundshift.plugins.registry import PluginRegistry
from groundshift.regions.resolver import UnknownRegionError, resolve_region

_WORLDCLIM_DIR = Path(__file__).parents[1] / "data" / "worldclim" / "10m"
_ERA5_DIR = Path(__file__).parents[1] / "data" / "era5"

_WORLDCLIM_TIME_RANGE = TimeRange(start=datetime(1970, 1, 1), end=datetime(2000, 12, 31))
_ERA5_TIME_RANGE = TimeRange(start=datetime(2015, 1, 1), end=datetime(2024, 12, 31))


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
        choices=["describe"],
        help="Pipeline phase to execute.",
    )
    run.add_argument(
        "--source",
        default="worldclim",
        choices=["worldclim", "era5"],
        help="Climate data source (default: worldclim).",
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
    if getattr(args, "source", "worldclim") == "era5":
        source = ERA5Source(_ERA5_DIR)
        time_range = _ERA5_TIME_RANGE
    else:
        source = WorldClimSource(_WORLDCLIM_DIR)
        time_range = _WORLDCLIM_TIME_RANGE
    runner = DescribePhaseRunner(source, PluginRegistry())
    result = runner.run(profile, region, time_range)

    score = result.score.values
    finite = score[~np.isnan(score)]
    viable = finite[finite > 0]

    print("Groundshift — Describe phase")
    print(f"  crop:    {args.crop}")
    print(f"  region:  {args.region}")
    print(f"  cells:   {len(finite)} scored, {len(viable)} viable (score > 0)")
    print(f"  score:   min={finite.min():.3f}  mean={finite.mean():.3f}  max={finite.max():.3f}")

    anchors = load_anchors_from_profile(profile)
    if anchors:
        anchor_scores = score_anchors(result, anchors)
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


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    if args.command == "run":
        run_describe(args)
