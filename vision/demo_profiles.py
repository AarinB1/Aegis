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
    note: str = ""


_PROFILES: dict[str, DemoVideoProfile] = {
    "DOD_111088902_12_18_hero": DemoVideoProfile(
        name="hero_casualty_closeup",
        roi=(300, 50, 1200, 980),
        recommended_frame_stride=6,
        clip_window_seconds=(2.9, 5.9),
        note="Focuses on the outdoor casualty treatment portion and removes the earlier scene change.",
    ),
    "DOD_110359890_best_indoor_treatment_00-00_00-09": DemoVideoProfile(
        name="indoor_treatment_focus",
        roi=(800, 340, 920, 640),
        recommended_frame_stride=6,
        clip_window_seconds=(0.0, 4.8),
        note="Keeps the indoor treatment sequence before the clip degrades into the darker transition frames.",
    ),
    "DOD_100500026_best_indoor_torso_assessment_01-23_01-35": DemoVideoProfile(
        name="indoor_torso_focus",
        roi=(700, 300, 1100, 720),
        recommended_frame_stride=6,
        clip_window_seconds=(0.0, 2.4),
        note="Limits the clip to the clean mannequin-torso view before medic occlusion and scene transition.",
    ),
}


def get_demo_profile(video_path: str | Path) -> Optional[DemoVideoProfile]:
    stem = Path(video_path).stem
    if stem in _PROFILES:
        return _PROFILES[stem]
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
