"""Export pre-computed opportunity zone results for the Groundshift API.

Writes data/results/emerging/{crop_id}_{region_id}.json — the file that
GET /api/v1/crops/{id}/emerging serves. Run after every prescribe pipeline
update to keep the API current.

Usage:
    python scripts/export_emerging.py --crop coffee --region ethiopia
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from groundshift.core.envelope.worldclim_source import WorldClimSource
from groundshift.core.envelope.yaml_loader import load_profile_from_yaml
from groundshift.core.opportunity.gain_zone_detector import GainZoneDetector
from groundshift.core.phases.describe import DescribePhaseRunner
from groundshift.core.phases.predict import PredictPhaseRunner
from groundshift.core.phases.prescribe import PrescribePhaseRunner
from groundshift.models.opportunity_zone import OpportunityZoneResult
from groundshift.models.time_range import TimeRange
from groundshift.plugins.registry import PluginRegistry
from groundshift.regions.resolver import UnknownRegionError, resolve_region

_PROFILES_DIR = Path(__file__).parent.parent / "crop_profiles"
_WORLDCLIM_DIR = Path(__file__).parent.parent / "data" / "worldclim" / "10m"
_CMIP6_DIR = Path(__file__).parent.parent / "data" / "cmip6"
_DEFAULT_RESULTS_DIR = Path(__file__).parent.parent / "data" / "results" / "emerging"

_WORLDCLIM_TIME_RANGE = TimeRange(start=datetime(1970, 1, 1), end=datetime(2000, 12, 31))
_CMIP6_TIME_RANGE = TimeRange(start=datetime(2015, 1, 1), end=datetime(2100, 12, 31))
_CMIP6_SCENARIOS = ["ssp245", "ssp585"]
_CMIP6_HORIZONS = [2040, 2060, 2100]


def _build_result_data(crop_id: str, region_id: str, opportunity: OpportunityZoneResult) -> dict:
    return {
        "crop_id": crop_id,
        "region": region_id,
        "zones": [
            {
                "scenario": z.scenario,
                "horizon_year": z.horizon_year,
                "cell_count": int(z.mask.values.sum()),
                "confidence": z.confidence,
            }
            for z in opportunity.zones
        ],
    }


def _output_path(results_dir: Path, crop_id: str, region_id: str) -> Path:
    return results_dir / f"{crop_id}_{region_id}.json"


def export_emerging(crop_id: str, region_id: str, results_dir: Path = _DEFAULT_RESULTS_DIR) -> Path:
    from groundshift.core.envelope.cmip6_source import CMIP6Source

    region = resolve_region(region_id)
    profile = load_profile_from_yaml(_PROFILES_DIR / f"{crop_id}.yaml")

    describe_result = DescribePhaseRunner(WorldClimSource(_WORLDCLIM_DIR), PluginRegistry()).run(
        profile, region, _WORLDCLIM_TIME_RANGE
    )

    predict_result = PredictPhaseRunner(
        CMIP6Source(_CMIP6_DIR),
        PluginRegistry(),
        scenarios=_CMIP6_SCENARIOS,
        horizons=_CMIP6_HORIZONS,
    ).run(profile, region, _CMIP6_TIME_RANGE)

    prescribe_result = PrescribePhaseRunner().run(describe_result, predict_result)
    opportunity = GainZoneDetector().detect(describe_result, prescribe_result)

    data = _build_result_data(crop_id, region_id, opportunity)
    results_dir.mkdir(parents=True, exist_ok=True)
    path = _output_path(results_dir, crop_id, region_id)
    path.write_text(json.dumps(data, indent=2))
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export emerging zone results for the API.")
    parser.add_argument("--crop", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--output-dir", type=Path, default=_DEFAULT_RESULTS_DIR)
    args = parser.parse_args()

    try:
        path = export_emerging(args.crop, args.region, results_dir=args.output_dir)
        print(f"Wrote {path}")
    except UnknownRegionError:
        raise SystemExit(f"Unknown region '{args.region}'.")
    except FileNotFoundError as exc:
        raise SystemExit(f"Required data not found: {exc}")


if __name__ == "__main__":
    main()
