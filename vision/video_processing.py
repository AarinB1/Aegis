from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional, Tuple

import cv2

from vision.contracts import VideoAnalysisResult, VideoFrameResult, WoundAnalysisResult, WoundRecord
from vision.render import draw_wounds
from vision.state_bridge import VisionStateBridge
from vision.summary import summarize_analysis, summarize_video_frames
from vision.tracker import SimpleTracker, Track
from vision.triage import calculate_overall_severity, calculate_priority_suggestion
from vision.wound_detection import WoundAnalyzer


class VideoProcessor:
    def __init__(
        self,
        analyzer: WoundAnalyzer,
        *,
        pixels_per_cm: Optional[float] = None,
        app_state: Any | None = None,
        casualty_factory: Any | None = None,
        suggestion_factory: Any | None = None,
    ) -> None:
        self.analyzer = analyzer
        self.pixels_per_cm = pixels_per_cm
        self.frame_index = 0
        self.tracker = SimpleTracker()
        self.state_bridge = VisionStateBridge(
            app_state=app_state,
            casualty_factory=casualty_factory,
            suggestion_factory=suggestion_factory,
        )
        self.last_result: dict | None = None

    def recv(self, frame) -> cv2.typing.MatLike:
        timestamp = time.time()
        rois_xywh = self.analyzer.detect_person_rois(frame)
        detections_xyxy = [self._xywh_to_xyxy(roi) for roi in rois_xywh]
        tracks = self.tracker.update(detections_xyxy, timestamp=timestamp)

        analysis = self.analyzer.analyze_image(frame, pixels_per_cm=self.pixels_per_cm)
        casualties = self._build_casualties(tracks, analysis)

        annotated_frame = draw_wounds(frame, analysis)
        for casualty in casualties:
            annotated_frame = self._draw_track_overlay(annotated_frame, casualty)

        self.state_bridge.publish(casualties=casualties, latest_frame=annotated_frame)
        self.last_result = {
            "frame_index": self.frame_index,
            "analysis": analysis,
            "summary": summarize_analysis(analysis, self.analyzer.detection_mode()).model_dump(),
            "casualties": casualties,
        }
        self.frame_index += 1
        return annotated_frame

    def process_video(
        self,
        video_path: str | Path,
        output_dir: str | Path,
        pixels_per_cm: Optional[float] = None,
        frame_stride: int = 1,
        max_frames: Optional[int] = None,
        write_annotated_video: bool = True,
    ) -> dict:
        source = Path(video_path)
        if not source.exists():
            raise FileNotFoundError(f"unable to read video: {source}")
        if frame_stride < 1:
            raise ValueError("frame_stride must be >= 1")

        capture = cv2.VideoCapture(str(source))
        if not capture.isOpened():
            raise ValueError(f"unable to open video: {source}")

        destination = Path(output_dir)
        destination.mkdir(parents=True, exist_ok=True)

        fps = capture.get(cv2.CAP_PROP_FPS)
        fps = float(fps) if fps and fps > 0 else 10.0
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        writer = None
        annotated_video_path: Optional[Path] = None
        processed_frames: list[VideoFrameResult] = []
        processed_count = 0
        frame_index = 0

        try:
            while True:
                if max_frames is not None and processed_count >= max_frames:
                    break

                ok, frame = capture.read()
                if not ok:
                    break

                if write_annotated_video and writer is None:
                    writer, annotated_video_path = self._create_video_writer(
                        destination / f"{source.stem}_annotated",
                        fps,
                        (frame.shape[1], frame.shape[0]),
                    )

                should_process = frame_index % frame_stride == 0
                if should_process:
                    previous_pixels_per_cm = self.pixels_per_cm
                    try:
                        self.pixels_per_cm = pixels_per_cm
                        annotated_frame = self.recv(frame)
                    finally:
                        self.pixels_per_cm = previous_pixels_per_cm
                    if self.last_result is None:
                        raise RuntimeError("video processor did not produce a frame result")
                    analysis = self.last_result["analysis"]
                    summary = summarize_analysis(analysis, self.analyzer.detection_mode())
                    processed_frames.append(
                        VideoFrameResult(
                            frame_index=frame_index,
                            timestamp_ms=int((frame_index / fps) * 1000),
                            analysis=WoundAnalysisResult.model_validate(analysis),
                            summary=summary,
                        )
                    )
                    processed_count += 1
                    annotated_frame = self._decorate_frame(
                        annotated_frame,
                        frame_index,
                        wound_count=analysis["wound_count"],
                        summary=summary,
                    )
                else:
                    annotated_frame = self._decorate_frame(frame, frame_index, wound_count=None, summary=None)

                if writer is not None:
                    writer.write(annotated_frame)

                frame_index += 1
        finally:
            capture.release()
            if writer is not None:
                writer.release()

        duration_ms = int((frame_count / fps) * 1000) if frame_count else int((frame_index / fps) * 1000)
        result = VideoAnalysisResult(
            source_video=str(source),
            annotated_video=str(annotated_video_path) if annotated_video_path is not None else None,
            fps=round(fps, 3),
            frame_count=max(frame_count, frame_index),
            processed_frames=len(processed_frames),
            frame_stride=frame_stride,
            duration_ms=duration_ms,
            summary=summarize_video_frames(processed_frames, self.analyzer.detection_mode()),
            frames=processed_frames,
        )
        return result.model_dump()

    def reset(self) -> None:
        self.frame_index = 0
        self.tracker.reset()
        self.state_bridge.reset()
        self.last_result = None

    def _build_casualties(self, tracks: list[Track], analysis: dict) -> list[dict]:
        grouped_wounds = self._group_wounds_by_track(tracks, analysis.get("wounds", []))
        casualties: list[dict] = []
        for track in tracks:
            wounds = grouped_wounds.get(track.track_id, [])
            wound_records = [WoundRecord.model_validate(wound) for wound in wounds]
            overall_severity = calculate_overall_severity(wound_records)
            priority = calculate_priority_suggestion(wound_records)
            casualties.append(
                {
                    "alias": track.alias,
                    "track_id": track.track_id,
                    "bbox": track.bbox,
                    "last_seen_ts": track.last_seen_ts,
                    "analysis": {
                        "wounds_detected": bool(wounds),
                        "wound_count": len(wounds),
                        "wounds": wounds,
                        "overall_severity": overall_severity,
                        "priority_suggestion": priority,
                        "confidence": self._casualty_confidence(wounds, analysis.get("confidence", 0.0)),
                        "image_quality": analysis.get("image_quality", 0.0),
                    },
                }
            )
        return casualties

    def _group_wounds_by_track(
        self,
        tracks: list[Track],
        wounds: list[dict],
    ) -> dict[int, list[dict]]:
        grouped: dict[int, list[dict]] = {track.track_id: [] for track in tracks}
        for wound in wounds:
            track = self._match_wound_to_track(wound, tracks)
            if track is not None:
                grouped[track.track_id].append(wound)
        return grouped

    def _match_wound_to_track(self, wound: dict, tracks: list[Track]) -> Track | None:
        location = wound["location"]
        center_x = location["x"] + (location["width"] / 2.0)
        center_y = location["y"] + (location["height"] / 2.0)
        for track in tracks:
            x1, y1, x2, y2 = track.bbox
            if x1 <= center_x <= x2 and y1 <= center_y <= y2:
                return track
        return tracks[0] if tracks else None

    def _casualty_confidence(self, wounds: list[dict], fallback: float) -> float:
        if not wounds:
            return round(float(min(fallback * 0.5, 0.99)), 3)
        return round(
            float(min(sum(wound["confidence"] for wound in wounds) / len(wounds), 0.99)),
            3,
        )

    def _xywh_to_xyxy(self, bbox: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        x, y, w, h = bbox
        return (x, y, x + w, y + h)

    def _draw_track_overlay(self, frame_bgr: cv2.typing.MatLike, casualty: dict):
        canvas = frame_bgr.copy()
        x1, y1, x2, y2 = casualty["bbox"]
        priority = casualty["analysis"]["priority_suggestion"]
        color = (0, 0, 255) if priority == "RED" else (0, 200, 255) if priority == "YELLOW" else (0, 180, 0)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            canvas,
            f"{casualty['alias']} #{casualty['track_id']} {priority}",
            (x1, max(24, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            color,
            2,
            cv2.LINE_AA,
        )
        return canvas

    def _create_video_writer(
        self,
        output_stem: Path,
        fps: float,
        size: Tuple[int, int],
    ) -> tuple[Optional[cv2.VideoWriter], Optional[Path]]:
        candidates = [
            (".mp4", "mp4v"),
            (".avi", "MJPG"),
            (".avi", "XVID"),
        ]

        for suffix, codec in candidates:
            path = output_stem.with_suffix(suffix)
            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*codec), fps, size)
            if writer.isOpened():
                return writer, path
            writer.release()

        return None, None

    def _decorate_frame(
        self,
        frame_bgr: cv2.typing.MatLike,
        frame_index: int,
        wound_count: Optional[int],
        summary,
    ):
        canvas = frame_bgr.copy()
        lines = [f"Frame {frame_index}"]
        if summary is not None:
            lines.append(f"Wounds {wound_count} | Max severity {summary.max_wound_severity:.2f}")
            lines.append(f"Bleeding {summary.bleeding_present}")
        else:
            lines.append("Skipped frame")

        for idx, line in enumerate(lines):
            cv2.putText(
                canvas,
                line,
                (16, 28 + (idx * 24)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
        return canvas
