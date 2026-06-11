from dataclasses import dataclass


@dataclass
class TransitionSuggestion:
    crop_id: str
    crop_name: str
    overlap_score: float


@dataclass
class TransitionResult:
    suggestions: list[TransitionSuggestion]
