"""Unit tests for LandTenurePlugin — PRINDEX-based tenure security scoring."""

from datetime import datetime

import numpy as np
import pytest
import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.layer_data import LayerData
from groundshift.models.time_range import TimeRange
from groundshift.plugins.land_tenure import LandTenurePlugin

_REGION = BoundingBox(min_lon=37.0, min_lat=5.0, max_lon=40.0, max_lat=9.0)
_TIME_RANGE = TimeRange(
    start=datetime(2030, 1, 1),
    end=datetime(2040, 12, 31),
    scenario="ssp245",
    horizon_year=2040,
)


def _make_layer(security_value: float) -> LayerData:
    da = xr.DataArray(
        np.full((3, 3), security_value, dtype="float32"),
        dims=["y", "x"],
    )
    return LayerData(
        plugin_id="land_tenure",
        region=_REGION,
        time_range=_TIME_RANGE,
        data=da,
        metadata={},
    )


class TestMetadata:
    def test_plugin_id_is_land_tenure(self, tmp_path):
        assert LandTenurePlugin(tmp_path).metadata.plugin_id == "land_tenure"

    def test_threat_tier_is_stress(self, tmp_path):
        assert LandTenurePlugin(tmp_path).metadata.threat_tier == "stress"

    def test_compatible_crops_includes_wildcard(self, tmp_path):
        assert "*" in LandTenurePlugin(tmp_path).metadata.compatible_crops

    def test_phase_applicability_includes_prescribe(self, tmp_path):
        assert "prescribe" in LandTenurePlugin(tmp_path).metadata.phase_applicability

    def test_version_is_set(self, tmp_path):
        assert LandTenurePlugin(tmp_path).metadata.version


class TestValidateConfig:
    def test_returns_true_for_any_crop_profile(self, tmp_path):
        plugin = LandTenurePlugin(tmp_path)
        for profile in [{"crop_id": "coffee_arabica"}, {"crop_id": "wheat"}, {}]:
            assert plugin.validate_config(profile) is True


class TestScore:
    def test_returns_suitability_modifier(self, tmp_path):
        from groundshift.models.suitability_modifier import SuitabilityModifier

        result = LandTenurePlugin(tmp_path).score(_make_layer(0.8), {})
        assert isinstance(result, SuitabilityModifier)

    def test_factor_value_equals_security_score(self, tmp_path):
        result = LandTenurePlugin(tmp_path).score(_make_layer(0.75), {})
        assert float(result.factor_value.mean()) == pytest.approx(0.75, abs=1e-4)

    def test_factor_value_low_security_is_low(self, tmp_path):
        result = LandTenurePlugin(tmp_path).score(_make_layer(0.15), {})
        assert float(result.factor_value.mean()) == pytest.approx(0.15, abs=1e-4)

    def test_factor_value_clipped_above_one(self, tmp_path):
        result = LandTenurePlugin(tmp_path).score(_make_layer(1.5), {})
        assert float(result.factor_value.mean()) == pytest.approx(1.0, abs=1e-4)

    def test_factor_value_clipped_below_zero(self, tmp_path):
        result = LandTenurePlugin(tmp_path).score(_make_layer(-0.3), {})
        assert float(result.factor_value.mean()) == pytest.approx(0.0, abs=1e-4)

    def test_probability_is_one_everywhere(self, tmp_path):
        result = LandTenurePlugin(tmp_path).score(_make_layer(0.5), {})
        assert float(result.probability.min()) == pytest.approx(1.0, abs=1e-6)
        assert float(result.probability.max()) == pytest.approx(1.0, abs=1e-6)

    def test_confidence_is_point_60(self, tmp_path):
        result = LandTenurePlugin(tmp_path).score(_make_layer(0.5), {})
        assert float(result.confidence.mean()) == pytest.approx(0.60, abs=1e-6)

    def test_metadata_contains_threat_tier_stress(self, tmp_path):
        result = LandTenurePlugin(tmp_path).score(_make_layer(0.5), {})
        assert result.metadata["threat_tier"] == "stress"

    def test_metadata_contains_mean_security_score(self, tmp_path):
        result = LandTenurePlugin(tmp_path).score(_make_layer(0.6), {})
        assert "mean_security_score" in result.metadata
        assert result.metadata["mean_security_score"] == pytest.approx(0.6, abs=1e-4)

    def test_plugin_id_on_modifier(self, tmp_path):
        result = LandTenurePlugin(tmp_path).score(_make_layer(0.5), {})
        assert result.plugin_id == "land_tenure"


class TestDescribe:
    def test_secure_label_when_factor_high(self, tmp_path):
        result = LandTenurePlugin(tmp_path).score(_make_layer(0.8), {})
        text = LandTenurePlugin(tmp_path).describe(result)
        assert "secure" in text.lower()

    def test_moderate_label_at_mid_security(self, tmp_path):
        result = LandTenurePlugin(tmp_path).score(_make_layer(0.5), {})
        text = LandTenurePlugin(tmp_path).describe(result)
        assert "moderate" in text.lower()

    def test_insecure_label_when_factor_low(self, tmp_path):
        result = LandTenurePlugin(tmp_path).score(_make_layer(0.2), {})
        text = LandTenurePlugin(tmp_path).describe(result)
        assert "insecure" in text.lower()

    def test_describe_includes_score_value(self, tmp_path):
        result = LandTenurePlugin(tmp_path).score(_make_layer(0.75), {})
        text = LandTenurePlugin(tmp_path).describe(result)
        assert "0.75" in text


class TestFetchData:
    def test_raises_file_not_found_if_missing(self, tmp_path):
        plugin = LandTenurePlugin(tmp_path)
        with pytest.raises(FileNotFoundError):
            plugin.fetch_data(_REGION, _TIME_RANGE)

    def test_reads_correct_filename(self, tmp_path):
        nc_path = tmp_path / "land_tenure_security.nc"
        da = xr.DataArray(
            np.full((4, 4), 0.7, dtype="float32"),
            coords={"lat": [9.0, 8.0, 7.0, 6.0], "lon": [37.0, 38.0, 39.0, 40.0]},
            dims=["lat", "lon"],
        )
        da.to_dataset(name="security_score").to_netcdf(nc_path)
        layer = LandTenurePlugin(tmp_path).fetch_data(_REGION, _TIME_RANGE)
        assert layer.plugin_id == "land_tenure"

    def test_returns_layer_data_with_data_array(self, tmp_path):
        nc_path = tmp_path / "land_tenure_security.nc"
        da = xr.DataArray(
            np.full((4, 4), 0.7, dtype="float32"),
            coords={"lat": [9.0, 8.0, 7.0, 6.0], "lon": [37.0, 38.0, 39.0, 40.0]},
            dims=["lat", "lon"],
        )
        da.to_dataset(name="security_score").to_netcdf(nc_path)
        layer = LandTenurePlugin(tmp_path).fetch_data(_REGION, _TIME_RANGE)
        assert isinstance(layer.data, xr.DataArray)

    def test_fetch_ignores_scenario_and_horizon(self, tmp_path):
        # Static baseline file — scenario/horizon don't change the filename
        nc_path = tmp_path / "land_tenure_security.nc"
        da = xr.DataArray(
            np.full((4, 4), 0.5, dtype="float32"),
            coords={"lat": [9.0, 8.0, 7.0, 6.0], "lon": [37.0, 38.0, 39.0, 40.0]},
            dims=["lat", "lon"],
        )
        da.to_dataset(name="security_score").to_netcdf(nc_path)
        tr_other = TimeRange(
            start=datetime(2060, 1, 1),
            end=datetime(2080, 12, 31),
            scenario="ssp585",
            horizon_year=2080,
        )
        layer = LandTenurePlugin(tmp_path).fetch_data(_REGION, tr_other)
        assert layer.plugin_id == "land_tenure"
