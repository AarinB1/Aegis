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
        analysis_roi: Tuple[int, int, int, int] | None = None,
        app_state: Any | None = None,
        casualty_factory: Any | None = None,
        suggestion_factory: Any | None = None,
    ) -> None:
        self.analyzer = analyzer
        self.pixels_per_cm = pixels_per_cm
        self.analysis_roi = analysis_roi
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
        work_frame = self._prepare_frame(frame)
        timestamp = time.time()
        rois_xywh = self.analyzer.detect_person_rois(work_frame)
        detections_xyxy = [self._xywh_to_xyxy(roi) for roi in rois_xywh]
        tracks = self.tracker.update(detections_xyxy, timestamp=timestamp)

        analysis = self.analyzer.analyze_image(work_frame, pixels_per_cm=self.pixels_per_cm)
        analysis = self._stabilize_analysis(analysis)
        casualties = self._build_casualties(tracks, analysis)
        scene_summary = self._build_scene_summary(casualties)
        summary = summarize_analysis(analysis, self.analyzer.detection_mode())
        annotated_frame = self._render_annotated_frame(
            work_frame,
            analysis=analysis,
            casualties=casualties,
            scene_summary=scene_summary,
            summary=summary,
            frame_index=self.frame_index,
        )

        self.state_bridge.publish(casualties=casualties, latest_frame=annotated_frame)
        self.last_result = {
            "frame_index": self.frame_index,
            "analysis": analysis,
            "summary": summary.model_dump(),
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
        start_seconds: float | None = None,
        end_seconds: float | None = None,
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
        start_frame = max(0, int(round((start_seconds or 0.0) * fps)))
        end_frame = frame_count
        if end_seconds is not None:
            end_frame = min(frame_count, max(start_frame + 1, int(round(end_seconds * fps))))
        if start_frame:
            capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        writer = None
        annotated_video_path: Optional[Path] = None
        processed_frames: list[VideoFrameResult] = []
        processed_count = 0
        frame_index = start_frame

        try:
            while True:
                if max_frames is not None and processed_count >= max_frames:
                    break
                if frame_index >= end_frame:
                    break

                ok, frame = capture.read()
                if not ok:
                    break

                work_frame = self._prepare_frame(frame)

                if write_annotated_video and writer is None:
                    writer, annotated_video_path = self._create_video_writer(
                        destination / f"{source.stem}_annotated",
                        fps,
                        (work_frame.shape[1], work_frame.shape[0]),
                    )

                relative_frame_index = frame_index - start_frame
                should_process = relative_frame_index % frame_stride == 0
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
                            frame_index=relative_frame_index,
                            timestamp_ms=int((relative_frame_index / fps) * 1000),
                            analysis=WoundAnalysisResult.model_validate(analysis),
                            summary=summary,
                            scene_summary=SceneSummary.model_validate(self.last_result["scene_summary"]),
                        )
                    )
                    processed_count += 1
                else:
                    annotated_frame = self._render_cached_frame(work_frame, frame_index)

                if writer is not None:
                    writer.write(annotated_frame)

                frame_index += 1
        finally:
            capture.release()
            if writer is not None:
                writer.release()

        effective_frame_count = max(0, end_frame - start_frame)
        duration_ms = int((effective_frame_count / fps) * 1000) if effective_frame_count else 0
        result = VideoAnalysisResult(
            source_video=str(source),
            annotated_video=str(annotated_video_path) if annotated_video_path is not None else None,
            fps=round(fps, 3),
            frame_count=effective_frame_count,
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

    def _prepare_frame(self, frame_bgr: cv2.typing.MatLike):
        if self.analysis_roi is None:
            return frame_bgr.copy()
        x, y, w, h = self.analysis_roi
        height, width = frame_bgr.shape[:2]
        x1 = max(0, min(x, width - 1))
        y1 = max(0, min(y, height - 1))
        x2 = max(x1 + 1, min(x + w, width))
        y2 = max(y1 + 1, min(y + h, height))
        return frame_bgr[y1:y2, x1:x2].copy()

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

    def _stabilize_analysis(self, analysis: dict) -> dict:
        if self.last_result is None:
            return analysis

        previous = self.last_result.get("analysis") or {}
        previous_wounds = previous.get("wounds", [])
        current_wounds = analysis.get("wounds", [])
        if not previous_wounds:
            return analysis

        stabilized_wounds: list[dict] = []
        used_previous: set[int] = set()

        for wound in current_wounds:
            match_index, match_iou = self._best_previous_match(wound, previous_wounds, used_previous)
            if match_index is not None and match_iou >= 0.12:
                stabilized_wounds.append(self._blend_wounds(previous_wounds[match_index], wound))
                used_previous.add(match_index)
                continue

            # Mid-scene, new wounds need stronger evidence or they will make the
            # demo look noisy. This keeps the overlay stable until we have a
            # better person-separated detector for medics vs casualty.
            if (
                wound.get("confidence", 0.0) >= 0.97
                or wound.get("severity", 0.0) >= 0.88
                or wound.get("size_cm2", 0.0) >= 24.0
            ):
                stabilized_wounds.append(wound)

        if not stabilized_wounds:
            stabilized_wounds = [
                wound
                for wound in (self._decay_wound(previous) for previous in previous_wounds[:2])
                if wound.get("confidence", 0.0) >= 0.2 and wound.get("severity", 0.0) >= 0.15
            ]

        overall_severity = calculate_overall_severity(
            [WoundRecord.model_validate(wound) for wound in stabilized_wounds]
        )
        priority = calculate_priority_suggestion(
            [WoundRecord.model_validate(wound) for wound in stabilized_wounds]
        )
        confidence = self._analysis_confidence(stabilized_wounds, analysis, previous)

        stabilized = dict(analysis)
        stabilized["wounds_detected"] = bool(stabilized_wounds)
        stabilized["wound_count"] = len(stabilized_wounds)
        stabilized["wounds"] = stabilized_wounds
        stabilized["overall_severity"] = overall_severity
        stabilized["priority_suggestion"] = priority
        stabilized["confidence"] = confidence
        return stabilized

    def _best_previous_match(
        self,
        wound: dict,
        previous_wounds: list[dict],
        used_previous: set[int],
    ) -> tuple[int | None, float]:
        best_index = None
        best_iou = 0.0
        current_bbox = self._wound_bbox_tuple(wound)
        for index, previous in enumerate(previous_wounds):
            if index in used_previous:
                continue
            iou = self._wound_iou(current_bbox, self._wound_bbox_tuple(previous))
            if iou > best_iou:
                best_iou = iou
                best_index = index
        return best_index, best_iou

    def _blend_wounds(self, previous: dict, current: dict) -> dict:
        prev_box = previous["location"]
        cur_box = current["location"]
        blended_box = {
            "x": int(round((0.45 * prev_box["x"]) + (0.55 * cur_box["x"]))),
            "y": int(round((0.45 * prev_box["y"]) + (0.55 * cur_box["y"]))),
            "width": int(round((0.45 * prev_box["width"]) + (0.55 * cur_box["width"]))),
            "height": int(round((0.45 * prev_box["height"]) + (0.55 * cur_box["height"]))),
        }
        blended = dict(current)
        blended["location"] = blended_box
        blended["severity"] = round((0.4 * previous["severity"]) + (0.6 * current["severity"]), 3)
        blended["size_cm2"] = round((0.45 * previous["size_cm2"]) + (0.55 * current["size_cm2"]), 2)
        blended["confidence"] = round(min((0.35 * previous["confidence"]) + (0.65 * current["confidence"]), 0.99), 3)
        blended["bleeding"] = bool(previous.get("bleeding") or current.get("bleeding"))
        blended["bleeding_detected"] = blended["bleeding"]
        blended["mask_area_px"] = int(round((0.45 * previous["mask_area_px"]) + (0.55 * current["mask_area_px"])))
        if current.get("type") == "unknown" and previous.get("type") is not None:
            blended["type"] = previous["type"]
        return blended

    def _decay_wound(self, wound: dict) -> dict:
        decayed = dict(wound)
        decayed["severity"] = round(max(wound.get("severity", 0.0) - 0.05, 0.0), 3)
        decayed["confidence"] = round(max(wound.get("confidence", 0.0) - 0.08, 0.0), 3)
        decayed["size_cm2"] = round(max(wound.get("size_cm2", 0.0) * 0.96, 0.0), 2)
        return decayed

    def _analysis_confidence(self, wounds: list[dict], current: dict, previous: dict) -> float:
        if not wounds:
            return round(max((0.85 * previous.get("confidence", 0.0)) - 0.08, 0.0), 3)
        wound_confidence = sum(wound.get("confidence", 0.0) for wound in wounds) / len(wounds)
        image_quality = current.get("image_quality", previous.get("image_quality", 0.0))
        return round(min((0.7 * wound_confidence) + (0.3 * image_quality), 0.99), 3)

    def _wound_bbox_tuple(self, wound: dict) -> tuple[int, int, int, int]:
        location = wound["location"]
        return (
            int(location["x"]),
            int(location["y"]),
            int(location["width"]),
            int(location["height"]),
        )

    def _wound_iou(
        self,
        box_a: tuple[int, int, int, int],
        box_b: tuple[int, int, int, int],
    ) -> float:
        ax, ay, aw, ah = box_a
        bx, by, bw, bh = box_b
        inter_x1 = max(ax, bx)
        inter_y1 = max(ay, by)
        inter_x2 = min(ax + aw, bx + bw)
        inter_y2 = min(ay + ah, by + bh)
        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return 0.0
        inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        area_a = aw * ah
        area_b = bw * bh
        return inter_area / max(area_a + area_b - inter_area, 1)

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
            0.76 if is_focus else 0.68,
            color,
            2 if is_focus else 1,
            cv2.LINE_AA,
        )
        return canvas

    def _render_annotated_frame(
        self,
        frame_bgr: cv2.typing.MatLike,
        *,
        analysis: dict,
        casualties: list[dict],
        scene_summary: SceneSummary,
        summary,
        frame_index: int,
        stale: bool = False,
    ):
        annotated_frame = draw_wounds(frame_bgr, analysis)
        for casualty in casualties:
            annotated_frame = self._draw_track_overlay(
                annotated_frame,
                casualty,
                focus_alias=scene_summary.top_casualty_alias,
            )
        annotated_frame = self._draw_scene_overlay(
            annotated_frame,
            frame_index=frame_index,
            summary=summary,
            scene_summary=scene_summary,
            stale=stale,
        )
        return annotated_frame

    def _render_cached_frame(self, frame_bgr: cv2.typing.MatLike, frame_index: int):
        if self.last_result is None:
            return self._decorate_idle_frame(frame_bgr, frame_index)

        return self._render_annotated_frame(
            frame_bgr,
            analysis=self.last_result["analysis"],
            casualties=self.last_result["casualties"],
            scene_summary=SceneSummary.model_validate(self.last_result["scene_summary"]),
            summary=summarize_analysis(self.last_result["analysis"], self.analyzer.detection_mode()),
            frame_index=frame_index,
            stale=True,
        )

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
        *,
        stale: bool = False,
    ):
        canvas = frame_bgr.copy()
        scale = max(min(canvas.shape[1] / 1920.0, canvas.shape[0] / 1080.0), 0.8)
        panel_width = int(min(canvas.shape[1] - 20, 640 * scale))
        panel_height = int(162 * scale)
        line_step = int(34 * scale)
        title_y = int(42 * scale)
        text_x = int(24 * scale)

        overlay = canvas.copy()
        cv2.rectangle(
            overlay,
            (10, 10),
            (10 + panel_width, 10 + panel_height),
            (12, 18, 32),
            thickness=-1,
        )
        cv2.addWeighted(overlay, 0.68, canvas, 0.32, 0, canvas)

        lines = [
            f"MASCAL Scene | Frame {frame_index}",
            (
                f"Tracked {scene_summary.tracked_casualties} | "
                f"Wounded {scene_summary.casualties_with_wounds} | "
                f"Immediate {scene_summary.immediate_casualties}"
            ),
            (
                f"Scene {summary.priority_suggestion} | "
                f"Severity {summary.max_wound_severity:.2f} | "
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
        if stale:
            lines.append("Using last stable perception state")

        for idx, line in enumerate(lines):
            cv2.putText(
                canvas,
                line,
                (text_x, title_y + (idx * line_step)),
                cv2.FONT_HERSHEY_SIMPLEX,
                (0.9 if idx == 0 else 0.74) * scale,
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

        scale = max(min(canvas.shape[1] / 1920.0, canvas.shape[0] / 1080.0), 0.8)
        panel_width = int(340 * scale)
        left = max(canvas.shape[1] - panel_width - 12, 12)
        overlay = canvas.copy()
        panel_height = int(44 * scale) + (len(scene_summary.top_casualties) * int(42 * scale))
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
            (left + int(14 * scale), 10 + int(26 * scale)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.72 * scale,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        for index, casualty in enumerate(scene_summary.top_casualties, start=1):
            y = 10 + int(26 * scale) + (index * int(38 * scale))
            color = (
                (0, 0, 255)
                if casualty.priority_suggestion == "RED"
                else (0, 200, 255)
                if casualty.priority_suggestion == "YELLOW"
                else (0, 180, 0)
            )
            cv2.putText(
                canvas,
                f"{index}. {casualty.alias} {casualty.priority_suggestion} | {casualty.attention_score:.2f}",
                (left + int(14 * scale), y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.68 * scale,
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
