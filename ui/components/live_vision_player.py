from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import threading
import time
from typing import Any

import cv2

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.demo_catalog import DEFAULT_HERO_VIDEO
from vision.demo_profiles import get_demo_profile
from vision.video_processing import VideoProcessor
from vision.wound_detection import WoundAnalyzer


class LiveVisionPlayerError(Exception):
    pass


class LiveVisionPlayer:
    def __init__(self, video_path: str | Path = DEFAULT_HERO_VIDEO) -> None:
        self.video_path = Path(video_path)
        if not self.video_path.exists():
            raise LiveVisionPlayerError(f"Live Vision video not found: {self.video_path}")

        self._profile = get_demo_profile(self.video_path)
        self._processor = self._build_processor()
        self._stop_event = threading.Event()
        self._resume_event = threading.Event()
        self._resume_event.set()
        self._state_lock = threading.RLock()
        self._state = "idle"
        self._run_anchor: float | None = None
        self._paused_t = 0.0
        self._video_thread: threading.Thread | None = None

    @property
    def status(self) -> dict[str, Any]:
        with self._state_lock:
            return {
                "state": self._state,
                "t": round(self._elapsed_locked(), 1),
            }

    def start(self) -> None:
        with self._state_lock:
            if self._state in {"playing", "paused"}:
                return

            self._processor.reset()
            self._stop_event = threading.Event()
            self._resume_event = threading.Event()
            self._resume_event.set()
            self._state = "playing"
            self._run_anchor = time.monotonic()
            self._paused_t = 0.0

            self._video_thread = threading.Thread(
                target=self._video_loop,
                name="live-vision-player",
                daemon=True,
            )
            self._video_thread.start()

        self._log(f"live vision player started: {self.video_path.name}")

    def pause(self) -> None:
        with self._state_lock:
            if self._state != "playing":
                return

            self._paused_t = self._elapsed_locked()
            self._state = "paused"
            self._resume_event.clear()

        self._log("live vision player paused")

    def resume(self) -> None:
        with self._state_lock:
            if self._state != "paused":
                return

            self._run_anchor = time.monotonic() - self._paused_t
            self._state = "playing"
            self._resume_event.set()

        self._log("live vision player resumed")

    def stop(self) -> None:
        with self._state_lock:
            if self._state == "idle":
                return
            self._state = "idle"
            self._run_anchor = None
            self._paused_t = 0.0

        self._stop_event.set()
        self._resume_event.set()

        if self._video_thread is not None and self._video_thread.is_alive():
            self._video_thread.join(timeout=2.0)

        self._video_thread = None
        self._processor.reset()
        self._log("live vision player stopped")

    def _build_processor(self) -> VideoProcessor:
        yolo_weights = ROOT / "models" / "yolov8n.pt"
        sam_checkpoint = ROOT / "models" / "mobile_sam.pt"
        analyzer = WoundAnalyzer(
            yolo_weights=str(yolo_weights) if yolo_weights.exists() else None,
            sam_checkpoint=str(sam_checkpoint) if sam_checkpoint.exists() else None,
        )
        analysis_roi = self._profile.roi if self._profile is not None else None
        return VideoProcessor(analyzer, analysis_roi=analysis_roi)

    def _elapsed_locked(self) -> float:
        if self._state == "playing" and self._run_anchor is not None:
            return max(0.0, time.monotonic() - self._run_anchor)
        if self._state == "paused":
            return max(0.0, self._paused_t)
        return 0.0

    def _wait_until_running(self) -> bool:
        while not self._stop_event.is_set():
            if self._resume_event.wait(timeout=0.1):
                return True
        return False

    def _sleep_with_control(self, seconds: float) -> bool:
        deadline = time.monotonic() + max(0.0, seconds)
        while not self._stop_event.is_set():
            if not self._wait_until_running():
                return False

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return True

            time.sleep(min(0.05, remaining))
        return False

    def _video_loop(self) -> None:
        while not self._stop_event.is_set():
            capture = cv2.VideoCapture(str(self.video_path))
            if not capture.isOpened():
                self._log(f"failed to open video: {self.video_path}")
                self._sleep_with_control(1.0)
                continue

            try:
                fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
                frame_interval = 1.0 / fps if fps > 0 else 1.0 / 15.0
                start_frame, end_frame = self._clip_bounds(capture, fps)
                if start_frame:
                    capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

                while not self._stop_event.is_set():
                    if not self._wait_until_running():
                        return

                    current_frame = int(capture.get(cv2.CAP_PROP_POS_FRAMES) or 0)
                    if end_frame is not None and current_frame >= end_frame:
                        capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

                    ok, frame = capture.read()
                    if not ok:
                        capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                        ok, frame = capture.read()
                        if not ok:
                            self._log("video loop hit EOF and failed to restart; retrying capture")
                            break

                    try:
                        self._processor.recv(frame)
                    except Exception as exc:
                        self._log(f"processor recv failed: {exc}")

                    if not self._sleep_with_control(frame_interval):
                        return
            finally:
                capture.release()

    def _clip_bounds(self, capture: cv2.VideoCapture, fps: float) -> tuple[int, int | None]:
        if fps <= 0:
            return (0, None)
        if self._profile is None or self._profile.clip_window_seconds is None:
            return (0, None)

        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        start_seconds, end_seconds = self._profile.clip_window_seconds
        start_frame = max(0, int(round(start_seconds * fps)))
        end_frame = max(start_frame + 1, int(round(end_seconds * fps)))
        if total_frames > 0:
            end_frame = min(end_frame, total_frames)
        return (start_frame, end_frame)

    def _log(self, message: str) -> None:
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        print(f"[{stamp}] live_vision_player: {message}", flush=True)
