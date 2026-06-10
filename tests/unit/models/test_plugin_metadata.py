import pytest

from groundshift.models.plugin_metadata import PluginMetadata


def _make_meta(**kwargs) -> PluginMetadata:
    defaults = dict(
        plugin_id="groundwater",
        name="Groundwater Stress (GRACE)",
        version="0.1.0",
        description="Applies a negative modifier in regions with aquifer depletion.",
        author="Test Author",
        compatible_crops=["*"],
        data_sources=["NASA GRACE-FO"],
        requires_network=True,
        phase_applicability=["describe", "predict"],
        threat_tier="stress",
    )
    return PluginMetadata(**{**defaults, **kwargs})


def test_plugin_metadata_stores_fields():
    meta = _make_meta()
    assert meta.plugin_id == "groundwater"
    assert meta.compatible_crops == ["*"]
    assert meta.requires_network is True


def test_plugin_metadata_stores_threat_tier():
    meta = _make_meta(threat_tier="existential")
    assert meta.threat_tier == "existential"


def test_plugin_metadata_custom_tier_stores_weight():
    meta = _make_meta(threat_tier="custom", custom_weight=2.0)
    assert meta.threat_tier == "custom"
    assert meta.custom_weight == 2.0


def test_plugin_metadata_custom_weight_defaults_to_one():
    meta = _make_meta(threat_tier="custom")
    assert meta.custom_weight == 1.0


def test_plugin_metadata_raises_on_invalid_tier():
    with pytest.raises(ValueError):
        _make_meta(threat_tier="nonsense")
