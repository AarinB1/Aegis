from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional, Tuple

import cv2

from vision.contracts import SceneSummary, VideoAnalysisResult, VideoFrameResult, WoundAnalysisResult, WoundRecord
from vision.render import draw_wounds
from vision.state_bridge import VisionStateBridge
from vision.summary import build_scene_summary, empty_scene_summary, summarize_analysis, summarize_video_frames
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
        self._attention_memory: dict[str, float] = {}

    def recv(self, frame) -> cv2.typing.MatLike:
        timestamp = time.time()
        rois_xywh = self.analyzer.detect_person_rois(frame)
        detections_xyxy = [self._xywh_to_xyxy(roi) for roi in rois_xywh]
        tracks = self.tracker.update(detections_xyxy, timestamp=timestamp)

        analysis = self.analyzer.analyze_image(frame, pixels_per_cm=self.pixels_per_cm)
        casualties = self._build_casualties(tracks, analysis)
        scene_summary = self._build_scene_summary(casualties)

        annotated_frame = draw_wounds(frame, analysis)
        for casualty in casualties:
            annotated_frame = self._draw_track_overlay(
                annotated_frame,
                casualty,
                focus_alias=scene_summary.top_casualty_alias,
            )
        annotated_frame = self._draw_scene_overlay(
            annotated_frame,
            frame_index=self.frame_index,
            summary=summarize_analysis(analysis, self.analyzer.detection_mode()),
            scene_summary=scene_summary,
        )

        self.state_bridge.publish(casualties=casualties, latest_frame=annotated_frame)
        self.last_result = {
            "frame_index": self.frame_index,
            "analysis": analysis,
            "summary": summarize_analysis(analysis, self.analyzer.detection_mode()).model_dump(),
            "scene_summary": scene_summary.model_dump(),
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
                            scene_summary=SceneSummary.model_validate(self.last_result["scene_summary"]),
                        )
                    )
                    processed_count += 1
                else:
                    annotated_frame = self._decorate_idle_frame(frame, frame_index)

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
            scene_summary=processed_frames[-1].scene_summary if processed_frames else empty_scene_summary(),
            frames=processed_frames,
        )
        return result.model_dump()

    def reset(self) -> None:
        self.frame_index = 0
        self.tracker.reset()
        self.state_bridge.reset()
        self.last_result = None
        self._attention_memory.clear()

    def _build_casualties(self, tracks: list[Track], analysis: dict) -> list[dict]:
        grouped_wounds = self._group_wounds_by_track(tracks, analysis.get("wounds", []))
        casualties: list[dict] = []
        for track in tracks:
            wounds = grouped_wounds.get(track.track_id, [])
            wound_records = [WoundRecord.model_validate(wound) for wound in wounds]
            overall_severity = calculate_overall_severity(wound_records)
            priority = calculate_priority_suggestion(wound_records)
            bleeding_wound_count = sum(1 for wound in wounds if wound["bleeding"])
            casualties.append(
                {
                    "alias": track.alias,
                    "track_id": track.track_id,
                    "bbox": track.bbox,
                    "last_seen_ts": track.last_seen_ts,
                    "bleeding_wound_count": bleeding_wound_count,
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
        return self._rank_casualties(casualties)

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

    def _draw_track_overlay(
        self,
        frame_bgr: cv2.typing.MatLike,
        casualty: dict,
        *,
        focus_alias: str | None,
    ):
        canvas = frame_bgr.copy()
        x1, y1, x2, y2 = casualty["bbox"]
        priority = casualty["analysis"]["priority_suggestion"]
        color = (0, 0, 255) if priority == "RED" else (0, 200, 255) if priority == "YELLOW" else (0, 180, 0)
        is_focus = casualty["alias"] == focus_alias
        box_thickness = 4 if is_focus else 2
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, box_thickness)
        cv2.putText(
            canvas,
            self._track_label(casualty, is_focus=is_focus),
            (x1, max(24, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.62 if is_focus else 0.58,
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

    def _draw_scene_overlay(
        self,
        frame_bgr: cv2.typing.MatLike,
        frame_index: int,
        summary,
        scene_summary: SceneSummary,
    ):
        canvas = frame_bgr.copy()
        overlay = canvas.copy()
        cv2.rectangle(overlay, (10, 10), (min(canvas.shape[1] - 10, 520), 138), (12, 18, 32), thickness=-1)
        cv2.addWeighted(overlay, 0.68, canvas, 0.32, 0, canvas)

        lines = [
            f"MASCAL Scene | Frame {frame_index}",
            (
                f"Tracked {scene_summary.tracked_casualties} | "
                f"Visible wounds {scene_summary.casualties_with_wounds} | "
                f"Immediate {scene_summary.immediate_casualties}"
            ),
            (
                f"Scene priority {summary.priority_suggestion} | "
                f"Peak visible severity {summary.max_wound_severity:.2f} | "
                f"Bleeding {summary.bleeding_present}"
            ),
        ]
        if scene_summary.top_casualty_alias is not None:
            lines.append(
                f"FOCUS {scene_summary.top_casualty_alias} {scene_summary.top_casualty_priority} | "
                f"{scene_summary.top_casualty_rationale}"
            )
        else:
            lines.append("FOCUS none | no visible casualty wound burden")

        for idx, line in enumerate(lines):
            cv2.putText(
                canvas,
                line,
                (20, 34 + (idx * 26)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.66 if idx == 0 else 0.6,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
        self._draw_priority_sidebar(canvas, scene_summary)
        return canvas

    def _decorate_idle_frame(self, frame_bgr: cv2.typing.MatLike, frame_index: int):
        canvas = frame_bgr.copy()
        cv2.putText(
            canvas,
            f"Frame {frame_index} | skipped for runtime budget",
            (16, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        return canvas

    def _rank_casualties(self, casualties: list[dict]) -> list[dict]:
        active_aliases = {casualty["alias"] for casualty in casualties}
        self._attention_memory = {
            alias: score for alias, score in self._attention_memory.items() if alias in active_aliases
        }

        for casualty in casualties:
            raw_score = self._raw_attention_score(casualty)
            previous = self._attention_memory.get(casualty["alias"], raw_score)
            smoothed = round(float(min((0.65 * previous) + (0.35 * raw_score), 1.0)), 3)
            casualty["attention_score"] = smoothed
            casualty["attention_rationale"] = self._attention_rationale(casualty)
            self._attention_memory[casualty["alias"]] = smoothed

        casualties.sort(
            key=lambda casualty: (
                self._priority_rank(casualty["analysis"]["priority_suggestion"]),
                casualty["attention_score"],
                casualty["analysis"]["overall_severity"],
                casualty["analysis"]["wound_count"],
            ),
            reverse=True,
        )
        return casualties

    def _build_scene_summary(self, casualties: list[dict]) -> SceneSummary:
        return build_scene_summary(casualties)

    def _raw_attention_score(self, casualty: dict) -> float:
        analysis = casualty["analysis"]
        wounds = analysis["wounds"]
        severity = float(analysis["overall_severity"])
        confidence = float(analysis["confidence"])
        wound_count = int(analysis["wound_count"])
        bleeding_count = int(casualty.get("bleeding_wound_count", 0))
        central_wound = any(wound.get("location_type") in {"torso", "head"} for wound in wounds)

        priority_base = {"RED": 0.55, "YELLOW": 0.32, "GREEN": 0.12}.get(
            analysis["priority_suggestion"],
            0.12,
        )
        score = priority_base
        score += min(severity * 0.28, 0.28)
        score += min(bleeding_count, 2) * 0.08
        score += min(wound_count, 3) * 0.04
        score += min(confidence * 0.05, 0.05)
        if central_wound:
            score += 0.06
        return round(float(min(score, 1.0)), 3)

    def _attention_rationale(self, casualty: dict) -> str:
        analysis = casualty["analysis"]
        wounds = analysis["wounds"]
        reasons: list[str] = []
        bleeding_count = casualty.get("bleeding_wound_count", 0)
        if bleeding_count:
            reasons.append("active bleeding")
        if any(wound.get("location_type") == "torso" for wound in wounds):
            reasons.append("torso wound")
        elif any(wound.get("location_type") == "head" for wound in wounds):
            reasons.append("head wound")
        if analysis["wound_count"] > 1:
            reasons.append(f"{analysis['wound_count']} visible wounds")
        elif analysis["overall_severity"] >= 0.7:
            reasons.append("high visible severity")
        if not reasons:
            reasons.append("monitor visible injuries")
        return ", ".join(reasons[:3])

    def _draw_priority_sidebar(self, canvas: cv2.typing.MatLike, scene_summary: SceneSummary) -> None:
        if not scene_summary.top_casualties:
            return

        panel_width = 270
        left = max(canvas.shape[1] - panel_width - 12, 12)
        overlay = canvas.copy()
        panel_height = 34 + (len(scene_summary.top_casualties) * 34)
        cv2.rectangle(
            overlay,
            (left, 10),
            (canvas.shape[1] - 10, min(canvas.shape[0] - 10, 10 + panel_height)),
            (16, 24, 40),
            thickness=-1,
        )
        cv2.addWeighted(overlay, 0.62, canvas, 0.38, 0, canvas)
        cv2.putText(
            canvas,
            "ATTENTION RANK",
            (left + 12, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.56,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        for index, casualty in enumerate(scene_summary.top_casualties, start=1):
            y = 32 + (index * 30)
            color = (
                (0, 0, 255)
                if casualty.priority_suggestion == "RED"
                else (0, 200, 255)
                if casualty.priority_suggestion == "YELLOW"
                else (0, 180, 0)
            )
            cv2.putText(
                canvas,
                f"{index}. {casualty.alias} {casualty.priority_suggestion}  score {casualty.attention_score:.2f}",
                (left + 12, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.54,
                color,
                2,
                cv2.LINE_AA,
            )

    def _priority_rank(self, priority: str) -> int:
        return {"RED": 3, "YELLOW": 2, "GREEN": 1}.get(priority, 0)

    def _track_label(self, casualty: dict, *, is_focus: bool) -> str:
        prefix = "FOCUS " if is_focus else ""
        return (
            f"{prefix}{casualty['alias']} #{casualty['track_id']} "
            f"{casualty['analysis']['priority_suggestion']} | "
            f"score {casualty.get('attention_score', 0.0):.2f}"
        )
