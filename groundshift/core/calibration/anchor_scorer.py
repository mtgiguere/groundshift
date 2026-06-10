from groundshift.models.anchor_score import AnchorScore
from groundshift.models.calibration_anchor import CalibrationAnchor
from groundshift.models.suitability_result import SuitabilityResult

# Minimum acceptable score by role. stress_reference has no floor — a
# declining score there confirms the model is working, not a problem.
_EXPECTED_MIN: dict[str, float | None] = {
    "origin_center": 0.70,
    "production_reference": 0.60,
    "stress_reference": None,
}


def score_anchors(
    result: SuitabilityResult,
    anchors: list[CalibrationAnchor],
) -> list[AnchorScore]:
    """Clip the suitability surface to each anchor region and return mean scores.

    Uses x (lon) and y (lat) coordinate names as produced by rioxarray.
    y coordinates are typically descending in rasters (N→S), so the slice
    is written max_lat→min_lat to select correctly on either orientation.
    """
    scores = []
    for anchor in anchors:
        bb = anchor.region

        clipped_score = result.score.sel(
            x=slice(bb.min_lon, bb.max_lon),
            y=slice(bb.max_lat, bb.min_lat),
        )
        clipped_conf = result.confidence.sel(
            x=slice(bb.min_lon, bb.max_lon),
            y=slice(bb.max_lat, bb.min_lat),
        )

        mean_score = float(clipped_score.mean(skipna=True))
        mean_conf = float(clipped_conf.mean(skipna=True))

        expected_min = _EXPECTED_MIN[anchor.role]
        alert = expected_min is not None and mean_score < expected_min

        scores.append(
            AnchorScore(
                anchor=anchor,
                score=mean_score,
                confidence=mean_conf,
                expected_min=expected_min,
                alert_triggered=alert,
            )
        )
    return scores
