from groundshift.models.bounding_box import BoundingBox
from groundshift.models.calibration_anchor import CalibrationAnchor


def load_anchors_from_profile(profile: dict) -> list[CalibrationAnchor]:
    """Return calibration anchors declared in a crop profile dict.

    Returns an empty list when the profile has no ``calibration_anchors`` key.
    """
    raw = profile.get("calibration_anchors", [])
    anchors = []
    for entry in raw:
        min_lon, min_lat, max_lon, max_lat = entry["bbox"]
        anchors.append(
            CalibrationAnchor(
                anchor_id=entry["id"],
                name=entry["name"],
                role=entry["role"],
                region=BoundingBox(
                    min_lon=min_lon,
                    min_lat=min_lat,
                    max_lon=max_lon,
                    max_lat=max_lat,
                ),
                notes=entry.get("notes", ""),
            )
        )
    return anchors
