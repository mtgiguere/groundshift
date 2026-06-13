"""Unit tests for PhenologyPlugin — GDD-based phenological synchrony."""

from datetime import datetime

import numpy as np
import pytest
import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.layer_data import LayerData
from groundshift.models.time_range import TimeRange
from groundshift.plugins.phenology import PhenologyPlugin

# coffee_arabica thresholds: temp viable 15-30°C, optimal 18-24°C
# GDD thresholds (× 365): viable_min=5475, optimal_min=6570, optimal_max=8760, viable_max=10950
_COFFEE_PROFILE = {
    "crop_id": "coffee_arabica",
    "climate_envelope": {
        "thresholds": {
            "mean_annual_temp_c": {
                "viable_min": 15.0,
                "optimal_min": 18.0,
                "optimal_max": 24.0,
                "viable_max": 30.0,
            }
        }
    },
}

_REGION = BoundingBox(min_lon=37.0, min_lat=5.0, max_lon=40.0, max_lat=9.0)
_TIME_RANGE = TimeRange(
    start=datetime(2030, 1, 1),
    end=datetime(2040, 12, 31),
    scenario="ssp245",
    horizon_year=2040,
)


def _make_layer(gdd_value: float) -> LayerData:
    da = xr.DataArray(
        np.full((3, 3), gdd_value, dtype="float32"),
        dims=["y", "x"],
    )
    return LayerData(
        plugin_id="phenology",
        region=_REGION,
        time_range=_TIME_RANGE,
        data=da,
        metadata={},
    )


class TestMetadata:
    def test_plugin_id_is_phenology(self, tmp_path):
        assert PhenologyPlugin(tmp_path).metadata.plugin_id == "phenology"

    def test_threat_tier_is_stress(self, tmp_path):
        assert PhenologyPlugin(tmp_path).metadata.threat_tier == "stress"

    def test_compatible_crops_includes_wildcard(self, tmp_path):
        assert "*" in PhenologyPlugin(tmp_path).metadata.compatible_crops

    def test_phase_applicability_includes_describe(self, tmp_path):
        assert "describe" in PhenologyPlugin(tmp_path).metadata.phase_applicability

    def test_version_is_set(self, tmp_path):
        assert PhenologyPlugin(tmp_path).metadata.version


class TestValidateConfig:
    def test_returns_true_for_any_crop_profile(self, tmp_path):
        plugin = PhenologyPlugin(tmp_path)
        for profile in [{"crop_id": "coffee_arabica"}, {"crop_id": "wheat"}, {}]:
            assert plugin.validate_config(profile) is True


class TestScore:
    def test_returns_suitability_modifier(self, tmp_path):
        from groundshift.models.suitability_modifier import SuitabilityModifier

        result = PhenologyPlugin(tmp_path).score(_make_layer(7000.0), _COFFEE_PROFILE)
        assert isinstance(result, SuitabilityModifier)

    def test_factor_value_is_one_in_optimal_range(self, tmp_path):
        # GDD=7000 is between optimal_min=6570 and optimal_max=8760
        result = PhenologyPlugin(tmp_path).score(_make_layer(7000.0), _COFFEE_PROFILE)
        assert float(result.factor_value.mean()) == pytest.approx(1.0, abs=1e-4)

    def test_factor_value_is_zero_below_viable_min(self, tmp_path):
        # GDD=3000 < viable_min=5475
        result = PhenologyPlugin(tmp_path).score(_make_layer(3000.0), _COFFEE_PROFILE)
        assert float(result.factor_value.mean()) == pytest.approx(0.0, abs=1e-4)

    def test_factor_value_is_zero_above_viable_max(self, tmp_path):
        # GDD=12000 > viable_max=10950
        result = PhenologyPlugin(tmp_path).score(_make_layer(12000.0), _COFFEE_PROFILE)
        assert float(result.factor_value.mean()) == pytest.approx(0.0, abs=1e-4)

    def test_factor_value_is_zero_at_viable_min(self, tmp_path):
        # At viable_min boundary: ramp_up=0
        result = PhenologyPlugin(tmp_path).score(_make_layer(5475.0), _COFFEE_PROFILE)
        assert float(result.factor_value.mean()) == pytest.approx(0.0, abs=1e-4)

    def test_factor_value_ramps_up_at_midpoint(self, tmp_path):
        # Midpoint of viable_min(5475) → optimal_min(6570): GDD=6022.5 → factor=0.5
        result = PhenologyPlugin(tmp_path).score(_make_layer(6022.5), _COFFEE_PROFILE)
        assert float(result.factor_value.mean()) == pytest.approx(0.5, abs=1e-3)

    def test_factor_value_ramps_down_at_midpoint(self, tmp_path):
        # Midpoint of optimal_max(8760) → viable_max(10950): GDD=9855 → factor=0.5
        result = PhenologyPlugin(tmp_path).score(_make_layer(9855.0), _COFFEE_PROFILE)
        assert float(result.factor_value.mean()) == pytest.approx(0.5, abs=1e-3)

    def test_factor_value_clipped_to_zero_one(self, tmp_path):
        result = PhenologyPlugin(tmp_path).score(_make_layer(0.0), _COFFEE_PROFILE)
        assert float(result.factor_value.min()) >= 0.0
        assert float(result.factor_value.max()) <= 1.0

    def test_probability_is_one_everywhere(self, tmp_path):
        result = PhenologyPlugin(tmp_path).score(_make_layer(7000.0), _COFFEE_PROFILE)
        assert float(result.probability.min()) == pytest.approx(1.0, abs=1e-6)
        assert float(result.probability.max()) == pytest.approx(1.0, abs=1e-6)

    def test_confidence_is_point_65(self, tmp_path):
        result = PhenologyPlugin(tmp_path).score(_make_layer(7000.0), _COFFEE_PROFILE)
        assert float(result.confidence.mean()) == pytest.approx(0.65, abs=1e-6)

    def test_metadata_contains_threat_tier_stress(self, tmp_path):
        result = PhenologyPlugin(tmp_path).score(_make_layer(7000.0), _COFFEE_PROFILE)
        assert result.metadata["threat_tier"] == "stress"

    def test_metadata_contains_mean_gdd(self, tmp_path):
        result = PhenologyPlugin(tmp_path).score(_make_layer(7000.0), _COFFEE_PROFILE)
        assert "mean_gdd" in result.metadata
        assert result.metadata["mean_gdd"] == pytest.approx(7000.0, abs=1.0)

    def test_plugin_id_on_modifier(self, tmp_path):
        result = PhenologyPlugin(tmp_path).score(_make_layer(7000.0), _COFFEE_PROFILE)
        assert result.plugin_id == "phenology"


class TestDescribe:
    def test_optimal_label_when_factor_near_one(self, tmp_path):
        # GDD=7000 → factor=1.0 (optimal range)
        result = PhenologyPlugin(tmp_path).score(_make_layer(7000.0), _COFFEE_PROFILE)
        text = PhenologyPlugin(tmp_path).describe(result)
        assert "optimal" in text.lower()

    def test_moderate_label_at_mid_factor(self, tmp_path):
        # GDD=6022.5 → factor≈0.5 (between viable and optimal min — moderate stress)
        result = PhenologyPlugin(tmp_path).score(_make_layer(6022.5), _COFFEE_PROFILE)
        text = PhenologyPlugin(tmp_path).describe(result)
        assert "moderate" in text.lower()

    def test_significant_label_when_factor_low(self, tmp_path):
        # GDD=3000 → factor=0.0 (well below viable min — significant stress)
        result = PhenologyPlugin(tmp_path).score(_make_layer(3000.0), _COFFEE_PROFILE)
        text = PhenologyPlugin(tmp_path).describe(result)
        assert "significant" in text.lower()

    def test_describe_includes_gdd_value(self, tmp_path):
        result = PhenologyPlugin(tmp_path).score(_make_layer(7000.0), _COFFEE_PROFILE)
        text = PhenologyPlugin(tmp_path).describe(result)
        assert "7000" in text


class TestFetchData:
    def test_raises_file_not_found_if_missing(self, tmp_path):
        plugin = PhenologyPlugin(tmp_path)
        with pytest.raises(FileNotFoundError):
            plugin.fetch_data(_REGION, _TIME_RANGE)

    def test_reads_correct_filename_for_scenario_and_horizon(self, tmp_path):
        nc_path = tmp_path / "phenology_gdd_ssp585_2060.nc"
        da = xr.DataArray(
            np.ones((4, 4), dtype="float32"),
            coords={"lat": [9.0, 8.0, 7.0, 6.0], "lon": [37.0, 38.0, 39.0, 40.0]},
            dims=["lat", "lon"],
        )
        da.to_dataset(name="gdd").to_netcdf(nc_path)
        layer = PhenologyPlugin(tmp_path).fetch_data(
            _REGION,
            TimeRange(
                start=datetime(2050, 1, 1),
                end=datetime(2060, 12, 31),
                scenario="ssp585",
                horizon_year=2060,
            ),
        )
        assert layer.plugin_id == "phenology"

    def test_returns_layer_data_with_data_array(self, tmp_path):
        nc_path = tmp_path / "phenology_gdd_ssp245_2040.nc"
        da = xr.DataArray(
            np.full((4, 4), 7000.0, dtype="float32"),
            coords={"lat": [9.0, 8.0, 7.0, 6.0], "lon": [37.0, 38.0, 39.0, 40.0]},
            dims=["lat", "lon"],
        )
        da.to_dataset(name="gdd").to_netcdf(nc_path)
        layer = PhenologyPlugin(tmp_path).fetch_data(_REGION, _TIME_RANGE)
        assert isinstance(layer.data, xr.DataArray)
