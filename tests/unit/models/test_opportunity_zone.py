import numpy as np
import xarray as xr

from groundshift.models.opportunity_zone import OpportunityZone, OpportunityZoneResult


def _mask() -> xr.DataArray:
    return xr.DataArray(np.array([[True, False], [False, True]]))


class TestOpportunityZone:
    def test_has_scenario_field(self):
        zone = OpportunityZone(scenario="ssp245", horizon_year=2040, mask=_mask(), confidence="low")
        assert zone.scenario == "ssp245"

    def test_has_horizon_year_field(self):
        zone = OpportunityZone(scenario="ssp245", horizon_year=2040, mask=_mask(), confidence="low")
        assert zone.horizon_year == 2040

    def test_has_mask_field(self):
        m = _mask()
        zone = OpportunityZone(scenario="ssp245", horizon_year=2040, mask=m, confidence="low")
        assert zone.mask is m

    def test_has_confidence_field(self):
        zone = OpportunityZone(scenario="ssp245", horizon_year=2040, mask=_mask(), confidence="low")
        assert zone.confidence == "low"


class TestOpportunityZoneResult:
    def test_has_zones_field(self):
        zone = OpportunityZone(scenario="ssp245", horizon_year=2040, mask=_mask(), confidence="low")
        result = OpportunityZoneResult(zones=[zone])
        assert len(result.zones) == 1

    def test_zones_are_opportunity_zone_instances(self):
        zone = OpportunityZone(scenario="ssp245", horizon_year=2040, mask=_mask(), confidence="low")
        result = OpportunityZoneResult(zones=[zone])
        assert isinstance(result.zones[0], OpportunityZone)

    def test_accepts_multiple_zones(self):
        zones = [
            OpportunityZone("ssp245", 2040, _mask(), "low"),
            OpportunityZone("ssp245", 2060, _mask(), "low"),
            OpportunityZone("ssp585", 2100, _mask(), "medium"),
        ]
        result = OpportunityZoneResult(zones=zones)
        assert len(result.zones) == 3
