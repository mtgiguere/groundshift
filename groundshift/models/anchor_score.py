from dataclasses import dataclass

from groundshift.models.calibration_anchor import CalibrationAnchor


@dataclass
class AnchorScore:
    anchor: CalibrationAnchor
    score: float
    confidence: float
    expected_min: float | None
    alert_triggered: bool
