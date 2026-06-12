"""Unit tests for build_plugin_registry — auto-detection from plugin data files."""

from groundshift.plugins.auto_registry import build_plugin_registry
from groundshift.plugins.drought_stress import DroughtStressPlugin
from groundshift.plugins.frost_risk import FrostRiskPlugin
from groundshift.plugins.heat_stress import HeatStressPlugin


class TestEmptyDir:
    def test_returns_empty_registry(self, tmp_path):
        registry = build_plugin_registry(tmp_path)
        assert registry.list_plugins() == []


class TestFrostRiskDetection:
    def test_registers_frost_risk_when_file_present(self, tmp_path):
        (tmp_path / "frost_risk_min_temp_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        ids = [p.metadata.plugin_id for p in registry.list_plugins()]
        assert "frost_risk" in ids

    def test_frost_risk_plugin_has_correct_type(self, tmp_path):
        (tmp_path / "frost_risk_min_temp_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        plugin = registry.get("frost_risk")
        assert isinstance(plugin, FrostRiskPlugin)

    def test_no_frost_files_no_registration(self, tmp_path):
        (tmp_path / "drought_stress_precip_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        ids = [p.metadata.plugin_id for p in registry.list_plugins()]
        assert "frost_risk" not in ids


class TestDroughtStressDetection:
    def test_registers_drought_stress_when_file_present(self, tmp_path):
        (tmp_path / "drought_stress_precip_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        ids = [p.metadata.plugin_id for p in registry.list_plugins()]
        assert "drought_stress" in ids

    def test_drought_stress_plugin_has_correct_type(self, tmp_path):
        (tmp_path / "drought_stress_precip_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        plugin = registry.get("drought_stress")
        assert isinstance(plugin, DroughtStressPlugin)

    def test_no_drought_files_no_registration(self, tmp_path):
        (tmp_path / "frost_risk_min_temp_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        ids = [p.metadata.plugin_id for p in registry.list_plugins()]
        assert "drought_stress" not in ids


class TestHeatStressDetection:
    def test_registers_heat_stress_when_file_present(self, tmp_path):
        (tmp_path / "heat_stress_mean_temp_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        ids = [p.metadata.plugin_id for p in registry.list_plugins()]
        assert "heat_stress" in ids

    def test_heat_stress_plugin_has_correct_type(self, tmp_path):
        (tmp_path / "heat_stress_mean_temp_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        plugin = registry.get("heat_stress")
        assert isinstance(plugin, HeatStressPlugin)

    def test_no_heat_files_no_registration(self, tmp_path):
        (tmp_path / "frost_risk_min_temp_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        ids = [p.metadata.plugin_id for p in registry.list_plugins()]
        assert "heat_stress" not in ids


class TestAllPluginsDetected:
    def test_all_three_registered_when_all_files_present(self, tmp_path):
        (tmp_path / "frost_risk_min_temp_ssp245_2040.nc").touch()
        (tmp_path / "drought_stress_precip_ssp245_2040.nc").touch()
        (tmp_path / "heat_stress_mean_temp_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        ids = {p.metadata.plugin_id for p in registry.list_plugins()}
        assert ids == {"frost_risk", "drought_stress", "heat_stress"}

    def test_plugin_data_dir_propagated(self, tmp_path):
        (tmp_path / "frost_risk_min_temp_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        plugin = registry.get("frost_risk")
        assert plugin._data_dir == tmp_path
