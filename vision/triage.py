from __future__ import annotations

from typing import Literal, Sequence

from vision.contracts import WoundRecord


LocationType = Literal["head", "torso", "limb"]
PrioritySuggestion = Literal["RED", "YELLOW", "GREEN"]


def infer_location_type(
    wound_bbox: tuple[int, int, int, int],
    person_roi: tuple[int, int, int, int],
) -> LocationType:
    wound_x, wound_y, wound_w, wound_h = wound_bbox
    roi_x, roi_y, roi_w, roi_h = person_roi

    center_x = wound_x + (wound_w / 2.0)
    center_y = wound_y + (wound_h / 2.0)
    relative_x = (center_x - roi_x) / max(roi_w, 1)
    relative_y = (center_y - roi_y) / max(roi_h, 1)

    if relative_y <= 0.22:
        return "head"
    if 0.22 < relative_y <= 0.65 and 0.2 <= relative_x <= 0.8:
        return "torso"
    return "limb"


def calculate_wound_severity(
    *,
    size_cm2: float,
    bleeding_detected: bool,
    location_type: LocationType,
    wound_type: str,
) -> float:
    severity = 0.0

    if size_cm2 > 10:
        severity += 0.4
    elif size_cm2 > 5:
        severity += 0.3
    else:
        severity += 0.1

    if bleeding_detected:
        severity += 0.3

    if location_type == "torso":
        severity += 0.2
    elif location_type == "head":
        severity += 0.15
    else:
        severity += 0.05

    if wound_type == "puncture":
        severity += 0.1
    elif wound_type == "laceration":
        severity += 0.08
    else:
        severity += 0.03

    return round(min(severity, 1.0), 3)


def calculate_overall_severity(wounds: Sequence[WoundRecord]) -> float:
    return round(min(sum(wound.severity for wound in wounds), 1.0), 3)


def calculate_priority_suggestion(wounds: Sequence[WoundRecord]) -> PrioritySuggestion:
    total_severity = sum(wound.severity for wound in wounds)
    active_bleeding_count = sum(1 for wound in wounds if wound.bleeding)

    if active_bleeding_count >= 2:
        return "RED"
    if total_severity > 0.7:
        return "RED"
    if any(wound.location_type == "torso" and wound.severity > 0.5 for wound in wounds):
        return "RED"

    if total_severity > 0.4:
        return "YELLOW"
    if active_bleeding_count >= 1:
        return "YELLOW"
    if len(wounds) > 2:
        return "YELLOW"

    return "GREEN"
