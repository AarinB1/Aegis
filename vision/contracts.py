from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


WoundType = Literal["laceration", "puncture", "bruise", "burn", "abrasion", "unknown"]
LocationType = Literal["head", "torso", "limb"]
PrioritySuggestion = Literal["RED", "YELLOW", "GREEN"]


class BoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class WoundRecord(BaseModel):
    location: BoundingBox
    severity: float = Field(ge=0.0, le=1.0)
    type: WoundType
    location_type: LocationType
    bleeding: bool
    bleeding_detected: bool
    size_cm2: float = Field(ge=0.0)
    confidence: float = Field(ge=0.0, le=1.0)
    mask_area_px: int = Field(ge=0)
    notes: Optional[str] = None


class WoundAnalysisResult(BaseModel):
    wounds_detected: bool
    wound_count: int = Field(ge=0)
    wounds: List[WoundRecord]
    overall_severity: float = Field(ge=0.0, le=1.0)
    priority_suggestion: PrioritySuggestion
    confidence: float = Field(ge=0.0, le=1.0)
    image_quality: float = Field(ge=0.0, le=1.0)


class VisionSummary(BaseModel):
    bleeding_present: bool
    bleeding_wound_count: int = Field(ge=0)
    total_visible_wound_area_cm2: float = Field(ge=0.0)
    max_wound_severity: float = Field(ge=0.0, le=1.0)
    overall_severity: float = Field(ge=0.0, le=1.0)
    highest_wound_confidence: float = Field(ge=0.0, le=1.0)
    priority_suggestion: PrioritySuggestion
    detection_mode: str


class MobileVisionResponse(BaseModel):
    request_id: str
    casualty_id: Optional[str] = None
    source_id: Optional[str] = None
    analysis: WoundAnalysisResult
    summary: VisionSummary


class VideoFrameResult(BaseModel):
    frame_index: int = Field(ge=0)
    timestamp_ms: int = Field(ge=0)
    analysis: WoundAnalysisResult
    summary: VisionSummary


class VideoSummary(BaseModel):
    bleeding_detected_any: bool
    peak_bleeding_wound_count: int = Field(ge=0)
    peak_total_visible_wound_area_cm2: float = Field(ge=0.0)
    max_wound_severity: float = Field(ge=0.0, le=1.0)
    peak_overall_severity: float = Field(ge=0.0, le=1.0)
    highest_wound_confidence: float = Field(ge=0.0, le=1.0)
    peak_wound_count: int = Field(ge=0)
    frames_with_wounds: int = Field(ge=0)
    processed_frame_count: int = Field(ge=0)
    priority_suggestion: PrioritySuggestion
    detection_mode: str


class VideoAnalysisResult(BaseModel):
    source_video: str
    annotated_video: Optional[str] = None
    fps: float = Field(ge=0.0)
    frame_count: int = Field(ge=0)
    processed_frames: int = Field(ge=0)
    frame_stride: int = Field(ge=1)
    duration_ms: int = Field(ge=0)
    summary: VideoSummary
    frames: List[VideoFrameResult]
