from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


@dataclass(frozen=True)
class DemoVideoProfile:
    name: str
    roi: Optional[Tuple[int, int, int, int]] = None
    recommended_frame_stride: int = 6
    clip_window_seconds: Optional[Tuple[float, float]] = None
    wound_focus_roi: Optional[Tuple[int, int, int, int]] = None
    max_wounds: Optional[int] = None
    max_casualties: Optional[int] = None
    publish_confidence_floor: float = 0.0
    publish_severity_floor: float = 0.0
    hide_track_overlay: bool = False
    note: str = ""


_PROFILES: dict[str, DemoVideoProfile] = {
    "DOD_111088902_12_18_hero": DemoVideoProfile(
        name="hero_casualty_closeup",
        roi=(300, 50, 1200, 980),
        recommended_frame_stride=6,
        clip_window_seconds=(2.9, 5.9),
        wound_focus_roi=(520, 40, 300, 260),
        max_wounds=1,
        max_casualties=1,
        publish_confidence_floor=0.82,
        publish_severity_floor=0.55,
        hide_track_overlay=True,
        note="Focuses on the outdoor casualty treatment portion and removes the earlier scene change.",
    ),
    "DOD_110359890_best_indoor_treatment_00-00_00-09": DemoVideoProfile(
        name="indoor_treatment_focus",
        roi=(800, 340, 920, 640),
        recommended_frame_stride=6,
        clip_window_seconds=(0.0, 4.8),
        max_wounds=1,
        max_casualties=1,
        publish_confidence_floor=0.72,
        publish_severity_floor=0.45,
        note="Keeps the indoor treatment sequence before the clip degrades into the darker transition frames.",
    ),
    "DOD_100500026_best_indoor_torso_assessment_01-23_01-35": DemoVideoProfile(
        name="indoor_torso_focus",
        roi=(700, 300, 1100, 720),
        recommended_frame_stride=6,
        clip_window_seconds=(0.0, 2.4),
        wound_focus_roi=(180, 120, 760, 430),
        max_wounds=1,
        max_casualties=1,
        publish_confidence_floor=0.8,
        publish_severity_floor=0.5,
        note="Limits the clip to the clean mannequin-torso view before medic occlusion and scene transition.",
    ),
}


def get_demo_profile(video_path: str | Path) -> Optional[DemoVideoProfile]:
    stem = Path(video_path).stem
    if stem in _PROFILES:
        return _PROFILES[stem]
    return None


def get_demo_profile_for_frame_shape(frame_shape: Tuple[int, int] | Tuple[int, int, int]) -> Optional[DemoVideoProfile]:
    height, width = int(frame_shape[0]), int(frame_shape[1])
    for profile in _PROFILES.values():
        if profile.roi is None:
            continue
        _, _, roi_width, roi_height = profile.roi
        if width == roi_width and height == roi_height:
            return profile
    return None


def parse_roi(value: str | None) -> Optional[Tuple[int, int, int, int]]:
    if value is None:
        return None
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("roi must be provided as x,y,width,height")
    x, y, w, h = (int(part) for part in parts)
    if w <= 0 or h <= 0:
        raise ValueError("roi width and height must be positive")
    return (x, y, w, h)
