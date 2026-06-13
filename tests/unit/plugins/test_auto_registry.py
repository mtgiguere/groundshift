"""Unit tests for build_plugin_registry — auto-detection from plugin data files."""

from groundshift.plugins.auto_registry import build_plugin_registry
from groundshift.plugins.cooperative_infra import CooperativeInfraPlugin
from groundshift.plugins.drought_stress import DroughtStressPlugin
from groundshift.plugins.frost_risk import FrostRiskPlugin
from groundshift.plugins.groundwater import GroundwaterPlugin
from groundshift.plugins.heat_stress import HeatStressPlugin
from groundshift.plugins.pest_disease import PestDiseasePlugin
from groundshift.plugins.phenology import PhenologyPlugin


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


class TestGroundwaterDetection:
    def test_registers_groundwater_when_file_present(self, tmp_path):
        (tmp_path / "groundwater_tws_baseline.nc").touch()
        registry = build_plugin_registry(tmp_path)
        ids = [p.metadata.plugin_id for p in registry.list_plugins()]
        assert "groundwater" in ids

    def test_groundwater_plugin_has_correct_type(self, tmp_path):
        (tmp_path / "groundwater_tws_baseline.nc").touch()
        registry = build_plugin_registry(tmp_path)
        plugin = registry.get("groundwater")
        assert isinstance(plugin, GroundwaterPlugin)

    def test_no_groundwater_files_no_registration(self, tmp_path):
        (tmp_path / "frost_risk_min_temp_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        ids = [p.metadata.plugin_id for p in registry.list_plugins()]
        assert "groundwater" not in ids


class TestPestDiseaseDetection:
    def test_registers_pest_disease_when_file_present(self, tmp_path):
        (tmp_path / "pest_disease_clr_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        ids = [p.metadata.plugin_id for p in registry.list_plugins()]
        assert "pest_disease" in ids

    def test_pest_disease_plugin_has_correct_type(self, tmp_path):
        (tmp_path / "pest_disease_clr_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        plugin = registry.get("pest_disease")
        assert isinstance(plugin, PestDiseasePlugin)

    def test_no_pest_disease_files_no_registration(self, tmp_path):
        (tmp_path / "frost_risk_min_temp_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        ids = [p.metadata.plugin_id for p in registry.list_plugins()]
        assert "pest_disease" not in ids


class TestCooperativeInfraDetection:
    def test_registers_cooperative_infra_when_file_present(self, tmp_path):
        (tmp_path / "cooperative_infra_access.nc").touch()
        registry = build_plugin_registry(tmp_path)
        ids = [p.metadata.plugin_id for p in registry.list_plugins()]
        assert "cooperative_infra" in ids

    def test_cooperative_infra_plugin_has_correct_type(self, tmp_path):
        (tmp_path / "cooperative_infra_access.nc").touch()
        registry = build_plugin_registry(tmp_path)
        plugin = registry.get("cooperative_infra")
        assert isinstance(plugin, CooperativeInfraPlugin)

    def test_no_cooperative_infra_files_no_registration(self, tmp_path):
        (tmp_path / "frost_risk_min_temp_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        ids = [p.metadata.plugin_id for p in registry.list_plugins()]
        assert "cooperative_infra" not in ids


class TestPhenologyDetection:
    def test_registers_phenology_when_file_present(self, tmp_path):
        (tmp_path / "phenology_gdd_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        ids = [p.metadata.plugin_id for p in registry.list_plugins()]
        assert "phenology" in ids

    def test_phenology_plugin_has_correct_type(self, tmp_path):
        (tmp_path / "phenology_gdd_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        plugin = registry.get("phenology")
        assert isinstance(plugin, PhenologyPlugin)

    def test_no_phenology_files_no_registration(self, tmp_path):
        (tmp_path / "frost_risk_min_temp_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        ids = [p.metadata.plugin_id for p in registry.list_plugins()]
        assert "phenology" not in ids


class TestAllPluginsDetected:
    def test_all_seven_registered_when_all_files_present(self, tmp_path):
        (tmp_path / "frost_risk_min_temp_ssp245_2040.nc").touch()
        (tmp_path / "drought_stress_precip_ssp245_2040.nc").touch()
        (tmp_path / "heat_stress_mean_temp_ssp245_2040.nc").touch()
        (tmp_path / "groundwater_tws_baseline.nc").touch()
        (tmp_path / "pest_disease_clr_ssp245_2040.nc").touch()
        (tmp_path / "cooperative_infra_access.nc").touch()
        (tmp_path / "phenology_gdd_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        ids = {p.metadata.plugin_id for p in registry.list_plugins()}
        assert ids == {
            "frost_risk",
            "drought_stress",
            "heat_stress",
            "groundwater",
            "pest_disease",
            "cooperative_infra",
            "phenology",
        }

    def test_plugin_data_dir_propagated(self, tmp_path):
        (tmp_path / "frost_risk_min_temp_ssp245_2040.nc").touch()
        registry = build_plugin_registry(tmp_path)
        plugin = registry.get("frost_risk")
        assert plugin._data_dir == tmp_path
