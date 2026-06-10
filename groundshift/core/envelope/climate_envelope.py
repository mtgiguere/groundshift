import xarray as xr

from groundshift.core.envelope.climate_source import ClimateDataSource
from groundshift.core.envelope.profile_loader import envelope_scorer_from_profile
from groundshift.models.bounding_box import BoundingBox
from groundshift.models.time_range import TimeRange


def compute_envelope(
    profile: dict,
    source: ClimateDataSource,
    region: BoundingBox,
    time_range: TimeRange,
) -> xr.DataArray:
    scorer = envelope_scorer_from_profile(profile)
    variables = profile["climate_envelope"]["thresholds"].keys()
    climate_data = {v: source.fetch(v, region, time_range) for v in variables}
    return scorer.score(climate_data)
