from __future__ import annotations

from typing import Sequence

from vision.contracts import VideoFrameResult, VideoSummary, VisionSummary


def summarize_analysis(analysis: dict, detection_mode: str) -> VisionSummary:
    wounds = analysis["wounds"]
    return VisionSummary(
        bleeding_present=any(wound["bleeding"] for wound in wounds),
        bleeding_wound_count=sum(1 for wound in wounds if wound["bleeding"]),
        total_visible_wound_area_cm2=round(sum(wound["size_cm2"] for wound in wounds), 2),
        max_wound_severity=max((wound["severity"] for wound in wounds), default=0.0),
        overall_severity=analysis.get("overall_severity", 0.0),
        highest_wound_confidence=max((wound["confidence"] for wound in wounds), default=0.0),
        priority_suggestion=analysis.get("priority_suggestion", "GREEN"),
        detection_mode=detection_mode,
    )


def summarize_video_frames(
    frames: Sequence[VideoFrameResult],
    detection_mode: str,
) -> VideoSummary:
    return VideoSummary(
        bleeding_detected_any=any(frame.summary.bleeding_present for frame in frames),
        peak_bleeding_wound_count=max((frame.summary.bleeding_wound_count for frame in frames), default=0),
        peak_total_visible_wound_area_cm2=max(
            (frame.summary.total_visible_wound_area_cm2 for frame in frames),
            default=0.0,
        ),
        max_wound_severity=max((frame.summary.max_wound_severity for frame in frames), default=0.0),
        peak_overall_severity=max((frame.summary.overall_severity for frame in frames), default=0.0),
        highest_wound_confidence=max(
            (frame.summary.highest_wound_confidence for frame in frames),
            default=0.0,
        ),
        peak_wound_count=max((frame.analysis.wound_count for frame in frames), default=0),
        frames_with_wounds=sum(1 for frame in frames if frame.analysis.wounds_detected),
        processed_frame_count=len(frames),
        priority_suggestion=_priority_from_frames(frames),
        detection_mode=detection_mode,
    )


def _priority_from_frames(frames: Sequence[VideoFrameResult]) -> str:
    priorities = [frame.summary.priority_suggestion for frame in frames]
    if "RED" in priorities:
        return "RED"
    if "YELLOW" in priorities:
        return "YELLOW"
    return "GREEN"
