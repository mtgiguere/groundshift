from groundshift.models.plugin_metadata import PluginMetadata


def test_plugin_metadata_stores_fields():
    meta = PluginMetadata(
        plugin_id="groundwater",
        name="Groundwater Stress (GRACE)",
        version="0.1.0",
        description="Applies a negative modifier in regions with aquifer depletion.",
        author="Test Author",
        compatible_crops=["*"],
        data_sources=["NASA GRACE-FO"],
        requires_network=True,
        phase_applicability=["describe", "predict"],
    )
    assert meta.plugin_id == "groundwater"
    assert meta.compatible_crops == ["*"]
    assert meta.requires_network is True
