from __future__ import annotations

from typing import Sequence

from vision.contracts import PrioritizedCasualty, SceneSummary, VideoFrameResult, VideoSummary, VisionSummary


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
        peak_tracked_casualties=max((frame.scene_summary.tracked_casualties for frame in frames), default=0),
        peak_casualties_with_wounds=max((frame.scene_summary.casualties_with_wounds for frame in frames), default=0),
        peak_immediate_casualties=max((frame.scene_summary.immediate_casualties for frame in frames), default=0),
        focus_casualty_alias=_focus_alias_from_frames(frames),
        focus_casualty_priority=_focus_priority_from_frames(frames),
    )


def _priority_from_frames(frames: Sequence[VideoFrameResult]) -> str:
    priorities = [frame.summary.priority_suggestion for frame in frames]
    if "RED" in priorities:
        return "RED"
    if "YELLOW" in priorities:
        return "YELLOW"
    return "GREEN"


def _focus_alias_from_frames(frames: Sequence[VideoFrameResult]) -> str | None:
    if not frames:
        return None
    focus_frame = max(
        frames,
        key=lambda frame: (
            frame.scene_summary.top_casualty_score,
            frame.scene_summary.immediate_casualties,
            frame.scene_summary.casualties_with_wounds,
        ),
    )
    return focus_frame.scene_summary.top_casualty_alias


def _focus_priority_from_frames(frames: Sequence[VideoFrameResult]) -> str:
    if not frames:
        return "GREEN"
    focus_frame = max(
        frames,
        key=lambda frame: (
            frame.scene_summary.top_casualty_score,
            frame.scene_summary.immediate_casualties,
            frame.scene_summary.casualties_with_wounds,
        ),
    )
    return focus_frame.scene_summary.top_casualty_priority


def empty_scene_summary() -> SceneSummary:
    return SceneSummary(
        tracked_casualties=0,
        casualties_with_wounds=0,
        immediate_casualties=0,
        delayed_casualties=0,
        minimal_casualties=0,
        top_casualty_alias=None,
        top_casualty_priority="GREEN",
        top_casualty_score=0.0,
        top_casualty_rationale="",
        top_casualties=[],
    )


def build_scene_summary(casualties: Sequence[dict]) -> SceneSummary:
    prioritized = [
        PrioritizedCasualty(
            alias=casualty["alias"],
            track_id=casualty["track_id"],
            priority_suggestion=casualty["analysis"]["priority_suggestion"],
            overall_severity=casualty["analysis"]["overall_severity"],
            wound_count=casualty["analysis"]["wound_count"],
            bleeding_wound_count=casualty.get("bleeding_wound_count", 0),
            confidence=casualty["analysis"]["confidence"],
            attention_score=casualty.get("attention_score", 0.0),
            rationale=casualty.get("attention_rationale", ""),
            bbox=casualty["bbox"],
        )
        for casualty in casualties
    ]
    top = prioritized[0] if prioritized else None
    return SceneSummary(
        tracked_casualties=len(casualties),
        casualties_with_wounds=sum(1 for casualty in casualties if casualty["analysis"]["wound_count"] > 0),
        immediate_casualties=sum(
            1 for casualty in casualties if casualty["analysis"]["priority_suggestion"] == "RED"
        ),
        delayed_casualties=sum(
            1 for casualty in casualties if casualty["analysis"]["priority_suggestion"] == "YELLOW"
        ),
        minimal_casualties=sum(
            1 for casualty in casualties if casualty["analysis"]["priority_suggestion"] == "GREEN"
        ),
        top_casualty_alias=None if top is None else top.alias,
        top_casualty_priority="GREEN" if top is None else top.priority_suggestion,
        top_casualty_score=0.0 if top is None else top.attention_score,
        top_casualty_rationale="" if top is None else top.rationale,
        top_casualties=prioritized[:3],
    )
