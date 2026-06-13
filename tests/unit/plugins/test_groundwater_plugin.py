from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.plugin_metadata import PluginMetadata
from groundshift.models.time_range import TimeRange
from groundshift.plugins.groundwater import GroundwaterPlugin

REGION = BoundingBox(min_lon=30.0, min_lat=0.0, max_lon=40.0, max_lat=10.0)
TIME_RANGE = TimeRange(
    start=datetime(2020, 1, 1),
    end=datetime(2023, 12, 31),
    scenario=None,
    horizon_year=None,
)
PROFILE = {"crop_id": "coffee"}


def _write_tws_nc(data_dir: Path, values: np.ndarray) -> None:
    lats = np.linspace(10, 0, values.shape[0])
    lons = np.linspace(30, 40, values.shape[1])
    da = xr.DataArray(values, coords={"lat": lats, "lon": lons}, dims=["lat", "lon"])
    ds = da.to_dataset(name="tws_anomaly_cm")
    ds.to_netcdf(data_dir / "groundwater_tws_baseline.nc")


@pytest.fixture
def data_dir(tmp_path):
    values = np.array([[-10.0, -30.0], [5.0, -60.0]], dtype=float)
    _write_tws_nc(tmp_path, values)
    return tmp_path


@pytest.fixture
def plugin(data_dir):
    return GroundwaterPlugin(data_dir)


class TestGroundwaterMetadata:
    def test_plugin_id_is_groundwater(self, plugin):
        assert plugin.metadata.plugin_id == "groundwater"

    def test_metadata_is_plugin_metadata_instance(self, plugin):
        assert isinstance(plugin.metadata, PluginMetadata)

    def test_threat_tier_is_stress(self, plugin):
        assert plugin.metadata.threat_tier == "stress"

    def test_requires_network_is_false(self, plugin):
        assert plugin.metadata.requires_network is False

    def test_phase_applicability_includes_describe(self, plugin):
        assert "describe" in plugin.metadata.phase_applicability


class TestGroundwaterValidateConfig:
    def test_returns_true_for_any_profile(self, plugin):
        assert plugin.validate_config({}) is True

    def test_returns_true_for_coffee(self, plugin):
        assert plugin.validate_config(PROFILE) is True

    def test_returns_bool(self, plugin):
        assert isinstance(plugin.validate_config(PROFILE), bool)


class TestGroundwaterFetchData:
    def test_returns_layer_data(self, plugin):
        from groundshift.models.layer_data import LayerData

        result = plugin.fetch_data(REGION, TIME_RANGE)
        assert isinstance(result, LayerData)

    def test_layer_data_plugin_id(self, plugin):
        result = plugin.fetch_data(REGION, TIME_RANGE)
        assert result.plugin_id == "groundwater"

    def test_layer_data_has_xarray(self, plugin):
        result = plugin.fetch_data(REGION, TIME_RANGE)
        assert isinstance(result.data, xr.DataArray)

    def test_raises_on_missing_file(self, tmp_path):
        plugin = GroundwaterPlugin(tmp_path)
        with pytest.raises(FileNotFoundError):
            plugin.fetch_data(REGION, TIME_RANGE)

    def test_fetch_ignores_scenario_and_horizon(self, data_dir):
        plugin = GroundwaterPlugin(data_dir)
        tr_projected = TimeRange(
            start=datetime(2035, 1, 1),
            end=datetime(2045, 12, 31),
            scenario="ssp585",
            horizon_year=2040,
        )
        result = plugin.fetch_data(REGION, tr_projected)
        assert isinstance(result.data, xr.DataArray)


class TestGroundwaterScore:
    def test_returns_suitability_modifier(self, plugin):
        from groundshift.models.suitability_modifier import SuitabilityModifier

        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, PROFILE)
        assert isinstance(result, SuitabilityModifier)

    def test_factor_value_in_unit_range(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, PROFILE)
        assert float(result.factor_value.min()) >= 0.0
        assert float(result.factor_value.max()) <= 1.0

    def test_probability_is_one_everywhere(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, PROFILE)
        assert float(result.probability.min()) == pytest.approx(1.0)

    def test_confidence_in_unit_range(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, PROFILE)
        assert float(result.confidence.min()) >= 0.0
        assert float(result.confidence.max()) <= 1.0

    def test_metadata_threat_tier_is_stress(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, PROFILE)
        assert result.metadata["threat_tier"] == "stress"

    def test_factor_one_when_no_depletion(self, tmp_path):
        values = np.zeros((2, 2), dtype=float)
        _write_tws_nc(tmp_path, values)
        layer = GroundwaterPlugin(tmp_path).fetch_data(REGION, TIME_RANGE)
        result = GroundwaterPlugin(tmp_path).score(layer, PROFILE)
        assert float(result.factor_value.mean()) == pytest.approx(1.0)

    def test_factor_zero_when_severely_depleted(self, tmp_path):
        values = np.full((2, 2), -100.0, dtype=float)
        _write_tws_nc(tmp_path, values)
        layer = GroundwaterPlugin(tmp_path).fetch_data(REGION, TIME_RANGE)
        result = GroundwaterPlugin(tmp_path).score(layer, PROFILE)
        assert float(result.factor_value.mean()) == pytest.approx(0.0)

    def test_heavier_depletion_lowers_factor(self, tmp_path):
        mild = np.full((2, 2), -10.0, dtype=float)
        severe = np.full((2, 2), -40.0, dtype=float)
        _write_tws_nc(tmp_path, mild)
        layer_mild = GroundwaterPlugin(tmp_path).fetch_data(REGION, TIME_RANGE)
        result_mild = GroundwaterPlugin(tmp_path).score(layer_mild, PROFILE)
        _write_tws_nc(tmp_path, severe)
        layer_severe = GroundwaterPlugin(tmp_path).fetch_data(REGION, TIME_RANGE)
        result_severe = GroundwaterPlugin(tmp_path).score(layer_severe, PROFILE)
        assert float(result_severe.factor_value.mean()) < float(result_mild.factor_value.mean())

    def test_metadata_includes_mean_tws_cm(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, PROFILE)
        assert "mean_tws_cm" in result.metadata


class TestGroundwaterDescribe:
    def test_returns_string(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, PROFILE)
        assert isinstance(plugin.describe(modifier), str)

    def test_returns_nonempty_string(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, PROFILE)
        assert len(plugin.describe(modifier)) > 0

    def test_low_label_when_no_depletion(self, tmp_path):
        values = np.zeros((2, 2), dtype=float)
        _write_tws_nc(tmp_path, values)
        plugin = GroundwaterPlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, PROFILE)
        assert "normal" in plugin.describe(modifier).lower()

    def test_severe_label_when_heavily_depleted(self, tmp_path):
        values = np.full((2, 2), -80.0, dtype=float)
        _write_tws_nc(tmp_path, values)
        plugin = GroundwaterPlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, PROFILE)
        assert "severe" in plugin.describe(modifier).lower()

    def test_moderate_label_at_mid_depletion(self, tmp_path):
        values = np.full((2, 2), -20.0, dtype=float)
        _write_tws_nc(tmp_path, values)
        plugin = GroundwaterPlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, PROFILE)
        assert "moderate" in plugin.describe(modifier).lower()
