from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from vision.demo_profiles import get_demo_profile

ROOT = Path(__file__).resolve().parents[2]
PRIMARY_HERO_VIDEO = ROOT / "assets" / "demo_videos" / "DOD_111088902_12_18_hero.mp4"
BACKUP_RECOGNITION_VIDEO = ROOT / "assets" / "demo_videos" / "DOD_110359890_best_indoor_treatment_00-00_00-09.mp4"
OPTIONAL_THIRD_VIDEO = ROOT / "assets" / "demo_videos" / "DOD_100500026_best_indoor_torso_assessment_01-23_01-35.mp4"
MASCAL_SCRIPT = ROOT / "scripts" / "demo_scenarios" / "mascal_90s.json"

# Backwards-compatible aliases for existing imports.
DEFAULT_HERO_VIDEO = PRIMARY_HERO_VIDEO
INDOOR_TREATMENT_VIDEO = BACKUP_RECOGNITION_VIDEO
INDOOR_ASSESSMENT_VIDEO = OPTIONAL_THIRD_VIDEO


@dataclass(frozen=True)
class CuratedClip:
    key: str
    label: str
    video_path: Path
    script_path: Path | None = None
    duration: float | None = None
    expose_in_menu: bool = False
    contract_role: str = "support"
    expected_output: tuple[str, ...] = ()


CURATED_DEMO_CLIPS: dict[str, CuratedClip] = {
    "primary": CuratedClip(
        key="primary",
        label="Scripted MASCAL (90s)",
        video_path=PRIMARY_HERO_VIDEO,
        script_path=MASCAL_SCRIPT,
        duration=90.0,
        expose_in_menu=True,
        contract_role="primary",
        expected_output=(
            "1 casualty",
            "1 primary face/neck bleeding wound",
            "no giant full-body track box",
            "no extra low-confidence roster entries",
        ),
    ),
    "backup": CuratedClip(
        key="backup",
        label="Backup Indoor Treatment",
        video_path=BACKUP_RECOGNITION_VIDEO,
        contract_role="backup",
    ),
    "optional_third": CuratedClip(
        key="optional_third",
        label="Optional Indoor Torso Assessment",
        video_path=OPTIONAL_THIRD_VIDEO,
        contract_role="optional_third",
    ),
}

MEDIC_POV_CLIP_MAP: dict[str, Path] = {
    "MEDIC_HAYES": CURATED_DEMO_CLIPS["backup"].video_path,
    "MEDIC_RIOS": CURATED_DEMO_CLIPS["optional_third"].video_path,
}


def menu_demo_scenarios() -> dict[str, dict[str, object] | None]:
    scenarios: dict[str, dict[str, object] | None] = {"Off": None}
    for clip in CURATED_DEMO_CLIPS.values():
        if not clip.expose_in_menu:
            continue
        scenarios[clip.label] = {
            "video_path": clip.video_path,
            "script_path": clip.script_path,
            "duration": clip.duration,
            "clip_key": clip.key,
        }
    return scenarios


def get_medic_pov_clip(medic_id: str) -> Path | None:
    clip_path = MEDIC_POV_CLIP_MAP.get(str(medic_id))
    if clip_path is None or not clip_path.exists():
        return None
    return clip_path


@lru_cache(maxsize=24)
def _video_profile(path_value: str) -> tuple[float, int, int | None, tuple[int, int, int, int] | None]:
    video_path = Path(path_value)
    capture = cv2.VideoCapture(str(video_path))
    try:
        if not capture.isOpened():
            return (0.0, 0, None, None)

        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        profile = get_demo_profile(video_path)

        start_frame = 0
        end_frame: int | None = None
        if fps > 0 and profile is not None and profile.clip_window_seconds is not None:
            start_seconds, end_seconds = profile.clip_window_seconds
            start_frame = max(0, int(round(start_seconds * fps)))
            end_frame = max(start_frame + 1, int(round(end_seconds * fps)))
            if total_frames > 0:
                end_frame = min(end_frame, total_frames)

        crop = getattr(profile, "roi", None) if profile is not None else None
        return (fps, start_frame, end_frame, crop)
    finally:
        capture.release()


@lru_cache(maxsize=256)
def _read_frame(path_value: str, frame_index: int) -> bytes | None:
    capture = cv2.VideoCapture(path_value)
    try:
        if not capture.isOpened():
            return None
        if frame_index > 0:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if not ok:
            return None
        success, encoded = cv2.imencode(".png", frame)
        if not success:
            return None
        return encoded.tobytes()
    finally:
        capture.release()


def sample_curated_frame(video_path: str | Path, elapsed_seconds: float | None = None):
    path = Path(video_path)
    if not path.exists():
        return None

    fps, start_frame, end_frame, crop = _video_profile(str(path))
    if fps <= 0:
        frame_index = 0
    else:
        clip_frames = max(1, (end_frame - start_frame) if end_frame is not None else int(round(fps * 3)))
        elapsed = max(0.0, float(elapsed_seconds or 0.0))
        frame_index = start_frame + (int(elapsed * fps) % clip_frames)

    payload = _read_frame(str(path), frame_index)
    if payload is None:
        return None

    image = cv2.imdecode(np.frombuffer(payload, dtype="uint8"), cv2.IMREAD_COLOR)
    if image is None:
        return None

    if crop is None:
        return image

    x, y, w, h = crop
    height, width = image.shape[:2]
    x1 = max(0, min(x, width - 1))
    y1 = max(0, min(y, height - 1))
    x2 = max(x1 + 1, min(x + w, width))
    y2 = max(y1 + 1, min(y + h, height))
    return image[y1:y2, x1:x2].copy()
