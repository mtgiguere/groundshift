from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.plugin_metadata import PluginMetadata
from groundshift.models.time_range import TimeRange
from groundshift.plugins.heat_stress import HeatStressPlugin

REGION = BoundingBox(min_lon=30.0, min_lat=0.0, max_lon=40.0, max_lat=10.0)
TIME_RANGE = TimeRange(
    start=datetime(2030, 1, 1),
    end=datetime(2040, 12, 31),
    scenario="ssp245",
    horizon_year=2040,
)
PROFILE = {"heat_max_threshold_c": 32.0}


def _write_mean_temp_nc(
    data_dir: Path, values: np.ndarray, scenario: str = "ssp245", horizon: int = 2040
) -> None:
    lats = np.linspace(10, 0, values.shape[0])
    lons = np.linspace(30, 40, values.shape[1])
    da = xr.DataArray(values, coords={"lat": lats, "lon": lons}, dims=["lat", "lon"])
    ds = da.to_dataset(name="mean_annual_temp_c")
    ds.to_netcdf(data_dir / f"heat_stress_mean_temp_{scenario}_{horizon}.nc")


@pytest.fixture
def data_dir(tmp_path):
    values = np.array([[20.0, 25.0], [28.0, 30.0]], dtype=float)
    _write_mean_temp_nc(tmp_path, values)
    return tmp_path


@pytest.fixture
def plugin(data_dir):
    return HeatStressPlugin(data_dir)


class TestHeatStressMetadata:
    def test_plugin_id_is_heat_stress(self, plugin):
        assert plugin.metadata.plugin_id == "heat_stress"

    def test_metadata_is_plugin_metadata_instance(self, plugin):
        assert isinstance(plugin.metadata, PluginMetadata)

    def test_threat_tier_is_stress(self, plugin):
        assert plugin.metadata.threat_tier == "stress"

    def test_requires_network_is_false(self, plugin):
        assert plugin.metadata.requires_network is False

    def test_phase_applicability_includes_describe(self, plugin):
        assert "describe" in plugin.metadata.phase_applicability


class TestHeatStressValidateConfig:
    def test_returns_true_when_threshold_present(self, plugin):
        assert plugin.validate_config(PROFILE) is True

    def test_returns_false_when_threshold_absent(self, plugin):
        assert plugin.validate_config({}) is False

    def test_returns_bool(self, plugin):
        assert isinstance(plugin.validate_config(PROFILE), bool)


class TestHeatStressFetchData:
    def test_returns_layer_data(self, plugin):
        from groundshift.models.layer_data import LayerData

        result = plugin.fetch_data(REGION, TIME_RANGE)
        assert isinstance(result, LayerData)

    def test_layer_data_plugin_id(self, plugin):
        result = plugin.fetch_data(REGION, TIME_RANGE)
        assert result.plugin_id == "heat_stress"

    def test_layer_data_has_xarray(self, plugin):
        result = plugin.fetch_data(REGION, TIME_RANGE)
        assert isinstance(result.data, xr.DataArray)

    def test_raises_on_missing_file(self, tmp_path):
        plugin = HeatStressPlugin(tmp_path)
        with pytest.raises(FileNotFoundError):
            plugin.fetch_data(REGION, TIME_RANGE)

    def test_uses_scenario_and_horizon_from_time_range(self, tmp_path):
        values = np.ones((2, 2), dtype=float) * 25.0
        _write_mean_temp_nc(tmp_path, values, scenario="ssp585", horizon=2060)
        plugin = HeatStressPlugin(tmp_path)
        tr = TimeRange(
            start=datetime(2050, 1, 1),
            end=datetime(2060, 12, 31),
            scenario="ssp585",
            horizon_year=2060,
        )
        result = plugin.fetch_data(REGION, tr)
        assert result.data is not None


class TestHeatStressScore:
    def test_returns_suitability_modifier(self, plugin):
        from groundshift.models.suitability_modifier import SuitabilityModifier

        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, PROFILE)
        assert isinstance(result, SuitabilityModifier)

    def test_probability_zero_when_temp_well_below_threshold(self, tmp_path):
        values = np.full((2, 2), 10.0, dtype=float)
        _write_mean_temp_nc(tmp_path, values)
        plugin = HeatStressPlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, PROFILE)
        assert float(result.probability.max()) == pytest.approx(0.0)

    def test_probability_one_when_temp_far_above_threshold(self, tmp_path):
        values = np.full((2, 2), 50.0, dtype=float)
        _write_mean_temp_nc(tmp_path, values)
        plugin = HeatStressPlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, PROFILE)
        assert float(result.probability.min()) == pytest.approx(1.0)

    def test_probability_in_unit_range(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, PROFILE)
        assert float(result.probability.min()) >= 0.0
        assert float(result.probability.max()) <= 1.0

    def test_factor_value_in_unit_range(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, PROFILE)
        assert float(result.factor_value.min()) >= 0.0
        assert float(result.factor_value.max()) <= 1.0

    def test_confidence_in_unit_range(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, PROFILE)
        assert float(result.confidence.min()) >= 0.0
        assert float(result.confidence.max()) <= 1.0

    def test_metadata_threat_tier_is_stress(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, PROFILE)
        assert result.metadata["threat_tier"] == "stress"

    def test_higher_threshold_reduces_probability(self, tmp_path):
        values = np.full((2, 2), 35.0, dtype=float)
        _write_mean_temp_nc(tmp_path, values)
        plugin = HeatStressPlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        low_thresh = plugin.score(layer, {"heat_max_threshold_c": 30.0})
        high_thresh = plugin.score(layer, {"heat_max_threshold_c": 38.0})
        assert float(high_thresh.probability.mean()) < float(low_thresh.probability.mean())

    def test_factor_value_equals_probability_complement(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, PROFILE)
        expected = 1.0 - result.probability
        assert float((result.factor_value - expected).max()) == pytest.approx(0.0, abs=1e-6)


class TestHeatStressDescribe:
    def test_returns_string(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, PROFILE)
        assert isinstance(plugin.describe(modifier), str)

    def test_returns_nonempty_string(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, PROFILE)
        assert len(plugin.describe(modifier)) > 0

    def test_low_stress_label_when_temp_cool(self, tmp_path):
        values = np.full((2, 2), 15.0, dtype=float)
        _write_mean_temp_nc(tmp_path, values)
        plugin = HeatStressPlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, PROFILE)
        assert "low" in plugin.describe(modifier)

    def test_high_stress_label_when_temp_extreme(self, tmp_path):
        values = np.full((2, 2), 50.0, dtype=float)
        _write_mean_temp_nc(tmp_path, values)
        plugin = HeatStressPlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, PROFILE)
        assert "high" in plugin.describe(modifier)
