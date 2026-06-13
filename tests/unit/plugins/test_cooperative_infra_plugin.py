from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.plugin_metadata import PluginMetadata
from groundshift.models.time_range import TimeRange
from groundshift.plugins.cooperative_infra import CooperativeInfraPlugin

REGION = BoundingBox(min_lon=35.0, min_lat=3.0, max_lon=42.0, max_lat=10.0)
TIME_RANGE = TimeRange(
    start=datetime(2020, 1, 1),
    end=datetime(2023, 12, 31),
    scenario=None,
    horizon_year=None,
)
PROFILE = {"crop_id": "coffee"}


def _write_access_nc(data_dir: Path, values: np.ndarray) -> None:
    lats = np.linspace(10, 3, values.shape[0])
    lons = np.linspace(35, 42, values.shape[1])
    da = xr.DataArray(values, coords={"lat": lats, "lon": lons}, dims=["lat", "lon"])
    ds = da.to_dataset(name="access_score")
    ds.to_netcdf(data_dir / "cooperative_infra_access.nc")


@pytest.fixture
def data_dir(tmp_path):
    values = np.array([[0.8, 0.4], [0.2, 0.9]], dtype=float)
    _write_access_nc(tmp_path, values)
    return tmp_path


@pytest.fixture
def plugin(data_dir):
    return CooperativeInfraPlugin(data_dir)


class TestCooperativeInfraMetadata:
    def test_plugin_id_is_cooperative_infra(self, plugin):
        assert plugin.metadata.plugin_id == "cooperative_infra"

    def test_metadata_is_plugin_metadata_instance(self, plugin):
        assert isinstance(plugin.metadata, PluginMetadata)

    def test_threat_tier_is_stress(self, plugin):
        assert plugin.metadata.threat_tier == "stress"

    def test_requires_network_is_false(self, plugin):
        assert plugin.metadata.requires_network is False

    def test_phase_applicability_includes_prescribe(self, plugin):
        assert "prescribe" in plugin.metadata.phase_applicability


class TestCooperativeInfraValidateConfig:
    def test_returns_true_for_any_crop(self, plugin):
        assert plugin.validate_config({}) is True

    def test_returns_true_for_coffee(self, plugin):
        assert plugin.validate_config(PROFILE) is True

    def test_returns_true_for_wheat(self, plugin):
        assert plugin.validate_config({"crop_id": "wheat"}) is True

    def test_returns_bool(self, plugin):
        assert isinstance(plugin.validate_config(PROFILE), bool)


class TestCooperativeInfraFetchData:
    def test_returns_layer_data(self, plugin):
        from groundshift.models.layer_data import LayerData

        result = plugin.fetch_data(REGION, TIME_RANGE)
        assert isinstance(result, LayerData)

    def test_layer_data_plugin_id(self, plugin):
        result = plugin.fetch_data(REGION, TIME_RANGE)
        assert result.plugin_id == "cooperative_infra"

    def test_layer_data_has_xarray(self, plugin):
        result = plugin.fetch_data(REGION, TIME_RANGE)
        assert isinstance(result.data, xr.DataArray)

    def test_raises_on_missing_file(self, tmp_path):
        plugin = CooperativeInfraPlugin(tmp_path)
        with pytest.raises(FileNotFoundError):
            plugin.fetch_data(REGION, TIME_RANGE)

    def test_fetch_ignores_scenario_and_horizon(self, data_dir):
        plugin = CooperativeInfraPlugin(data_dir)
        tr_projected = TimeRange(
            start=datetime(2035, 1, 1),
            end=datetime(2045, 12, 31),
            scenario="ssp585",
            horizon_year=2040,
        )
        result = plugin.fetch_data(REGION, tr_projected)
        assert isinstance(result.data, xr.DataArray)


class TestCooperativeInfraScore:
    def test_returns_suitability_modifier(self, plugin):
        from groundshift.models.suitability_modifier import SuitabilityModifier

        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, PROFILE)
        assert isinstance(result, SuitabilityModifier)

    def test_factor_value_equals_access_score(self, tmp_path):
        values = np.full((2, 2), 0.6, dtype=float)
        _write_access_nc(tmp_path, values)
        layer = CooperativeInfraPlugin(tmp_path).fetch_data(REGION, TIME_RANGE)
        result = CooperativeInfraPlugin(tmp_path).score(layer, PROFILE)
        assert float(result.factor_value.mean()) == pytest.approx(0.6, abs=1e-4)

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

    def test_better_access_gives_higher_factor(self, tmp_path):
        _write_access_nc(tmp_path, np.full((2, 2), 0.3, dtype=float))
        layer_low = CooperativeInfraPlugin(tmp_path).fetch_data(REGION, TIME_RANGE)
        result_low = CooperativeInfraPlugin(tmp_path).score(layer_low, PROFILE)

        _write_access_nc(tmp_path, np.full((2, 2), 0.9, dtype=float))
        layer_high = CooperativeInfraPlugin(tmp_path).fetch_data(REGION, TIME_RANGE)
        result_high = CooperativeInfraPlugin(tmp_path).score(layer_high, PROFILE)

        assert float(result_high.factor_value.mean()) > float(result_low.factor_value.mean())

    def test_full_access_factor_is_one(self, tmp_path):
        _write_access_nc(tmp_path, np.ones((2, 2), dtype=float))
        layer = CooperativeInfraPlugin(tmp_path).fetch_data(REGION, TIME_RANGE)
        result = CooperativeInfraPlugin(tmp_path).score(layer, PROFILE)
        assert float(result.factor_value.mean()) == pytest.approx(1.0)

    def test_no_access_factor_is_zero(self, tmp_path):
        _write_access_nc(tmp_path, np.zeros((2, 2), dtype=float))
        layer = CooperativeInfraPlugin(tmp_path).fetch_data(REGION, TIME_RANGE)
        result = CooperativeInfraPlugin(tmp_path).score(layer, PROFILE)
        assert float(result.factor_value.mean()) == pytest.approx(0.0)


class TestCooperativeInfraDescribe:
    def test_returns_string(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, PROFILE)
        assert isinstance(plugin.describe(modifier), str)

    def test_returns_nonempty_string(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, PROFILE)
        assert len(plugin.describe(modifier)) > 0

    def test_good_access_label(self, tmp_path):
        _write_access_nc(tmp_path, np.ones((2, 2), dtype=float))
        plugin = CooperativeInfraPlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, PROFILE)
        assert "good" in plugin.describe(modifier).lower()

    def test_poor_access_label(self, tmp_path):
        _write_access_nc(tmp_path, np.zeros((2, 2), dtype=float))
        plugin = CooperativeInfraPlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, PROFILE)
        assert "poor" in plugin.describe(modifier).lower()

    def test_limited_access_label(self, tmp_path):
        _write_access_nc(tmp_path, np.full((2, 2), 0.4, dtype=float))
        plugin = CooperativeInfraPlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, PROFILE)
        assert "limited" in plugin.describe(modifier).lower()
