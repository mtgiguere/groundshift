from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.plugin_metadata import PluginMetadata
from groundshift.models.time_range import TimeRange
from groundshift.plugins.frost_risk import FrostRiskPlugin

REGION = BoundingBox(min_lon=30.0, min_lat=0.0, max_lon=40.0, max_lat=10.0)
TIME_RANGE = TimeRange(
    start=datetime(2030, 1, 1),
    end=datetime(2040, 12, 31),
    scenario="ssp245",
    horizon_year=2040,
)


def _write_min_temp_nc(
    data_dir: Path, values: np.ndarray, scenario: str = "ssp245", horizon: int = 2040
) -> None:
    lats = np.linspace(10, 0, values.shape[0])
    lons = np.linspace(30, 40, values.shape[1])
    da = xr.DataArray(values, coords={"lat": lats, "lon": lons}, dims=["lat", "lon"])
    ds = da.to_dataset(name="min_annual_temp_c")
    ds.to_netcdf(data_dir / f"frost_risk_min_temp_{scenario}_{horizon}.nc")


@pytest.fixture
def data_dir(tmp_path):
    values = np.array([[5.0, 10.0], [15.0, 20.0]], dtype=float)
    _write_min_temp_nc(tmp_path, values)
    return tmp_path


@pytest.fixture
def plugin(data_dir):
    return FrostRiskPlugin(data_dir)


class TestFrostRiskMetadata:
    def test_plugin_id_is_frost_risk(self, plugin):
        assert plugin.metadata.plugin_id == "frost_risk"

    def test_metadata_is_plugin_metadata_instance(self, plugin):
        assert isinstance(plugin.metadata, PluginMetadata)

    def test_threat_tier_is_existential(self, plugin):
        assert plugin.metadata.threat_tier == "existential"

    def test_requires_network_is_false(self, plugin):
        assert plugin.metadata.requires_network is False

    def test_phase_applicability_includes_describe(self, plugin):
        assert "describe" in plugin.metadata.phase_applicability


class TestFrostRiskValidateConfig:
    def test_returns_true_for_empty_profile(self, plugin):
        assert plugin.validate_config({}) is True

    def test_returns_true_for_profile_with_frost_threshold(self, plugin):
        assert plugin.validate_config({"frost_threshold_c": -2.0}) is True

    def test_returns_bool(self, plugin):
        assert isinstance(plugin.validate_config({}), bool)


class TestFrostRiskFetchData:
    def test_returns_layer_data(self, plugin):
        from groundshift.models.layer_data import LayerData

        result = plugin.fetch_data(REGION, TIME_RANGE)
        assert isinstance(result, LayerData)

    def test_layer_data_plugin_id(self, plugin):
        result = plugin.fetch_data(REGION, TIME_RANGE)
        assert result.plugin_id == "frost_risk"

    def test_layer_data_has_xarray(self, plugin):
        result = plugin.fetch_data(REGION, TIME_RANGE)
        assert isinstance(result.data, xr.DataArray)

    def test_raises_on_missing_file(self, tmp_path):
        plugin = FrostRiskPlugin(tmp_path)
        with pytest.raises(FileNotFoundError):
            plugin.fetch_data(REGION, TIME_RANGE)

    def test_uses_scenario_and_horizon_from_time_range(self, tmp_path):
        values = np.ones((2, 2), dtype=float) * 15.0
        _write_min_temp_nc(tmp_path, values, scenario="ssp585", horizon=2060)
        plugin = FrostRiskPlugin(tmp_path)
        tr = TimeRange(
            start=datetime(2050, 1, 1),
            end=datetime(2060, 12, 31),
            scenario="ssp585",
            horizon_year=2060,
        )
        result = plugin.fetch_data(REGION, tr)
        assert result.data is not None


class TestFrostRiskScore:
    def test_returns_suitability_modifier(self, plugin):
        from groundshift.models.suitability_modifier import SuitabilityModifier

        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, {})
        assert isinstance(result, SuitabilityModifier)

    def test_factor_value_is_zero_everywhere(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, {})
        assert float(result.factor_value.max()) == 0.0

    def test_probability_zero_for_warm_cell(self, tmp_path):
        # min_temp well above threshold → probability = 0
        values = np.array([[20.0, 20.0], [20.0, 20.0]], dtype=float)
        _write_min_temp_nc(tmp_path, values)
        plugin = FrostRiskPlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, {"frost_threshold_c": 0.0})
        assert float(result.probability.max()) == pytest.approx(0.0)

    def test_probability_one_for_frozen_cell(self, tmp_path):
        # min_temp well below threshold → probability = 1
        values = np.array([[-20.0, -20.0], [-20.0, -20.0]], dtype=float)
        _write_min_temp_nc(tmp_path, values)
        plugin = FrostRiskPlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, {"frost_threshold_c": 0.0})
        assert float(result.probability.min()) == pytest.approx(1.0)

    def test_probability_in_unit_range(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, {})
        assert float(result.probability.min()) >= 0.0
        assert float(result.probability.max()) <= 1.0

    def test_confidence_in_unit_range(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, {})
        assert float(result.confidence.min()) >= 0.0
        assert float(result.confidence.max()) <= 1.0

    def test_metadata_threat_tier_is_existential(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, {})
        assert result.metadata["threat_tier"] == "existential"

    def test_custom_frost_threshold_shifts_risk(self, tmp_path):
        # Same temperature, higher threshold → higher frost probability
        values = np.full((2, 2), 5.0, dtype=float)
        _write_min_temp_nc(tmp_path, values)
        plugin = FrostRiskPlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        low_thresh = plugin.score(layer, {"frost_threshold_c": 0.0})
        high_thresh = plugin.score(layer, {"frost_threshold_c": 10.0})
        assert float(high_thresh.probability.mean()) > float(low_thresh.probability.mean())


class TestFrostRiskDescribe:
    def test_returns_string(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, {})
        assert isinstance(plugin.describe(modifier), str)

    def test_returns_nonempty_string(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, {})
        assert len(plugin.describe(modifier)) > 0

    def test_low_risk_label_when_probability_near_zero(self, tmp_path):
        values = np.full((2, 2), 30.0, dtype=float)
        _write_min_temp_nc(tmp_path, values)
        plugin = FrostRiskPlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, {"frost_threshold_c": 0.0})
        assert "low" in plugin.describe(modifier)

    def test_high_risk_label_when_probability_near_one(self, tmp_path):
        values = np.full((2, 2), -30.0, dtype=float)
        _write_min_temp_nc(tmp_path, values)
        plugin = FrostRiskPlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, {"frost_threshold_c": 0.0})
        assert "high" in plugin.describe(modifier)
