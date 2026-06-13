"""Auto-register plugins when their data files are present in plugin_data_dir."""

from pathlib import Path

from groundshift.plugins.drought_stress import DroughtStressPlugin
from groundshift.plugins.frost_risk import FrostRiskPlugin
from groundshift.plugins.groundwater import GroundwaterPlugin
from groundshift.plugins.heat_stress import HeatStressPlugin
from groundshift.plugins.registry import PluginRegistry


def build_plugin_registry(plugin_data_dir: Path) -> PluginRegistry:
    """Return a PluginRegistry populated with any plugin whose data files exist."""
    registry = PluginRegistry()

    if any(plugin_data_dir.glob("frost_risk_min_temp_*.nc")):
        registry.register(FrostRiskPlugin(plugin_data_dir))

    if any(plugin_data_dir.glob("drought_stress_precip_*.nc")):
        registry.register(DroughtStressPlugin(plugin_data_dir))

    if any(plugin_data_dir.glob("heat_stress_mean_temp_*.nc")):
        registry.register(HeatStressPlugin(plugin_data_dir))

    if any(plugin_data_dir.glob("groundwater_tws_*.nc")):
        registry.register(GroundwaterPlugin(plugin_data_dir))

    return registry
