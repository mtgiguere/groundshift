from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.plugin_metadata import PluginMetadata
from groundshift.models.time_range import TimeRange
from groundshift.plugins.pest_disease import PestDiseasePlugin

REGION = BoundingBox(min_lon=35.0, min_lat=3.0, max_lon=42.0, max_lat=10.0)
TIME_RANGE = TimeRange(
    start=datetime(2030, 1, 1),
    end=datetime(2040, 12, 31),
    scenario="ssp245",
    horizon_year=2040,
)
COFFEE_PROFILE = {"crop_id": "coffee"}
NON_COFFEE_PROFILE = {"crop_id": "wheat"}


def _write_clr_nc(
    data_dir: Path,
    values: np.ndarray,
    scenario: str = "ssp245",
    horizon: int = 2040,
) -> None:
    lats = np.linspace(10, 3, values.shape[0])
    lons = np.linspace(35, 42, values.shape[1])
    da = xr.DataArray(values, coords={"lat": lats, "lon": lons}, dims=["lat", "lon"])
    ds = da.to_dataset(name="clr_risk_index")
    ds.to_netcdf(data_dir / f"pest_disease_clr_{scenario}_{horizon}.nc")


@pytest.fixture
def data_dir(tmp_path):
    values = np.array([[0.6, 0.3], [0.8, 0.1]], dtype=float)
    _write_clr_nc(tmp_path, values)
    return tmp_path


@pytest.fixture
def plugin(data_dir):
    return PestDiseasePlugin(data_dir)


class TestPestDiseaseMetadata:
    def test_plugin_id_is_pest_disease(self, plugin):
        assert plugin.metadata.plugin_id == "pest_disease"

    def test_metadata_is_plugin_metadata_instance(self, plugin):
        assert isinstance(plugin.metadata, PluginMetadata)

    def test_threat_tier_is_existential(self, plugin):
        assert plugin.metadata.threat_tier == "existential"

    def test_requires_network_is_false(self, plugin):
        assert plugin.metadata.requires_network is False

    def test_phase_applicability_includes_describe(self, plugin):
        assert "describe" in plugin.metadata.phase_applicability

    def test_compatible_crops_includes_coffee(self, plugin):
        assert "coffee" in plugin.metadata.compatible_crops


class TestPestDiseaseValidateConfig:
    def test_returns_true_for_coffee(self, plugin):
        assert plugin.validate_config({"crop_id": "coffee"}) is True

    def test_returns_true_for_coffee_arabica(self, plugin):
        assert plugin.validate_config({"crop_id": "coffee_arabica"}) is True

    def test_returns_false_for_wheat(self, plugin):
        assert plugin.validate_config({"crop_id": "wheat"}) is False

    def test_returns_false_for_tea(self, plugin):
        assert plugin.validate_config({"crop_id": "tea"}) is False

    def test_returns_false_for_empty_profile(self, plugin):
        assert plugin.validate_config({}) is False

    def test_returns_bool(self, plugin):
        assert isinstance(plugin.validate_config(COFFEE_PROFILE), bool)


class TestPestDiseaseFetchData:
    def test_returns_layer_data(self, plugin):
        from groundshift.models.layer_data import LayerData

        result = plugin.fetch_data(REGION, TIME_RANGE)
        assert isinstance(result, LayerData)

    def test_layer_data_plugin_id(self, plugin):
        result = plugin.fetch_data(REGION, TIME_RANGE)
        assert result.plugin_id == "pest_disease"

    def test_layer_data_has_xarray(self, plugin):
        result = plugin.fetch_data(REGION, TIME_RANGE)
        assert isinstance(result.data, xr.DataArray)

    def test_raises_on_missing_file(self, tmp_path):
        plugin = PestDiseasePlugin(tmp_path)
        with pytest.raises(FileNotFoundError):
            plugin.fetch_data(REGION, TIME_RANGE)

    def test_uses_scenario_and_horizon_from_time_range(self, tmp_path):
        values = np.ones((2, 2), dtype=float) * 0.5
        _write_clr_nc(tmp_path, values, scenario="ssp585", horizon=2060)
        plugin = PestDiseasePlugin(tmp_path)
        tr = TimeRange(
            start=datetime(2050, 1, 1),
            end=datetime(2060, 12, 31),
            scenario="ssp585",
            horizon_year=2060,
        )
        result = plugin.fetch_data(REGION, tr)
        assert result.data is not None


class TestPestDiseaseScore:
    def test_returns_suitability_modifier(self, plugin):
        from groundshift.models.suitability_modifier import SuitabilityModifier

        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, COFFEE_PROFILE)
        assert isinstance(result, SuitabilityModifier)

    def test_factor_value_in_unit_range(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, COFFEE_PROFILE)
        assert float(result.factor_value.min()) >= 0.0
        assert float(result.factor_value.max()) <= 1.0

    def test_probability_in_unit_range(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, COFFEE_PROFILE)
        assert float(result.probability.min()) >= 0.0
        assert float(result.probability.max()) <= 1.0

    def test_confidence_in_unit_range(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, COFFEE_PROFILE)
        assert float(result.confidence.min()) >= 0.0
        assert float(result.confidence.max()) <= 1.0

    def test_metadata_threat_tier_is_existential(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, COFFEE_PROFILE)
        assert result.metadata["threat_tier"] == "existential"

    def test_factor_zero_always_for_existential_tier(self, tmp_path):
        # Existential: if stressor occurs, it eliminates suitability. factor=0 always.
        for risk in [0.0, 0.5, 1.0]:
            values = np.full((2, 2), risk, dtype=float)
            _write_clr_nc(tmp_path, values)
            layer = PestDiseasePlugin(tmp_path).fetch_data(REGION, TIME_RANGE)
            result = PestDiseasePlugin(tmp_path).score(layer, COFFEE_PROFILE)
            assert float(result.factor_value.mean()) == pytest.approx(0.0)

    def test_probability_zero_when_clr_risk_zero(self, tmp_path):
        values = np.zeros((2, 2), dtype=float)
        _write_clr_nc(tmp_path, values)
        plugin = PestDiseasePlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, COFFEE_PROFILE)
        assert float(result.probability.mean()) == pytest.approx(0.0)

    def test_higher_risk_raises_probability(self, tmp_path):
        _write_clr_nc(tmp_path, np.full((2, 2), 0.2, dtype=float))
        layer_low = PestDiseasePlugin(tmp_path).fetch_data(REGION, TIME_RANGE)
        result_low = PestDiseasePlugin(tmp_path).score(layer_low, COFFEE_PROFILE)

        _write_clr_nc(tmp_path, np.full((2, 2), 0.8, dtype=float))
        layer_high = PestDiseasePlugin(tmp_path).fetch_data(REGION, TIME_RANGE)
        result_high = PestDiseasePlugin(tmp_path).score(layer_high, COFFEE_PROFILE)

        assert float(result_high.probability.mean()) > float(result_low.probability.mean())

    def test_probability_equals_clr_risk(self, tmp_path):
        values = np.full((2, 2), 0.7, dtype=float)
        _write_clr_nc(tmp_path, values)
        plugin = PestDiseasePlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        result = plugin.score(layer, COFFEE_PROFILE)
        assert float(result.probability.mean()) == pytest.approx(0.7, abs=1e-4)


class TestPestDiseaseDescribe:
    def test_returns_string(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, COFFEE_PROFILE)
        assert isinstance(plugin.describe(modifier), str)

    def test_returns_nonempty_string(self, plugin):
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, COFFEE_PROFILE)
        assert len(plugin.describe(modifier)) > 0

    def test_low_label_when_risk_negligible(self, tmp_path):
        _write_clr_nc(tmp_path, np.zeros((2, 2), dtype=float))
        plugin = PestDiseasePlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, COFFEE_PROFILE)
        assert "low" in plugin.describe(modifier).lower()

    def test_high_label_when_risk_severe(self, tmp_path):
        _write_clr_nc(tmp_path, np.ones((2, 2), dtype=float))
        plugin = PestDiseasePlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, COFFEE_PROFILE)
        assert "high" in plugin.describe(modifier).lower()

    def test_moderate_label_at_mid_risk(self, tmp_path):
        _write_clr_nc(tmp_path, np.full((2, 2), 0.5, dtype=float))
        plugin = PestDiseasePlugin(tmp_path)
        layer = plugin.fetch_data(REGION, TIME_RANGE)
        modifier = plugin.score(layer, COFFEE_PROFILE)
        assert "moderate" in plugin.describe(modifier).lower()
