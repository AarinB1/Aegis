from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import sys
import threading
import time
from typing import Any

import cv2

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from schema import AISuggestion, Intervention, TriageCategory
from scripts.seed_fake_data import seed
from shared.state import app_state


class DemoPlayerError(Exception):
    pass


class DemoPlayer:
    def __init__(self, video_path: str | Path, script_path: str | Path) -> None:
        self.video_path = Path(video_path)
        self.script_path = Path(script_path)

        if not self.video_path.exists():
            raise DemoPlayerError(f"Demo video not found: {self.video_path}")
        if not self.script_path.exists():
            raise DemoPlayerError(f"Demo script not found: {self.script_path}")

        self._scenario = self._load_scenario(self.script_path)
        self._events: list[dict[str, Any]] = self._scenario["events"]
        self.duration = max((float(event["at"]) for event in self._events), default=0.0)

        self._stop_event = threading.Event()
        self._resume_event = threading.Event()
        self._resume_event.set()
        self._state_lock = threading.RLock()
        self._state = "idle"
        self._cycle_anchor: float | None = None
        self._paused_t = 0.0
        self._video_thread: threading.Thread | None = None
        self._scheduler_thread: threading.Thread | None = None

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

            self._stop_event = threading.Event()
            self._resume_event = threading.Event()
            self._resume_event.set()
            self._state = "playing"
            self._cycle_anchor = time.monotonic()
            self._paused_t = 0.0

            self._video_thread = threading.Thread(
                target=self._video_loop,
                name="demo-video-player",
                daemon=True,
            )
            self._scheduler_thread = threading.Thread(
                target=self._scheduler_loop,
                name="demo-event-scheduler",
                daemon=True,
            )
            self._video_thread.start()
            self._scheduler_thread.start()

        self._log("demo player started")

    def pause(self) -> None:
        with self._state_lock:
            if self._state != "playing":
                return

            self._paused_t = self._elapsed_locked()
            self._state = "paused"
            self._resume_event.clear()

        self._log("demo player paused")

    def resume(self) -> None:
        with self._state_lock:
            if self._state != "paused":
                return

            self._cycle_anchor = time.monotonic() - self._paused_t
            self._state = "playing"
            self._resume_event.set()

        self._log("demo player resumed")

    def stop(self) -> None:
        with self._state_lock:
            if self._state == "idle":
                return
            self._state = "idle"
            self._cycle_anchor = None
            self._paused_t = 0.0

        self._stop_event.set()
        self._resume_event.set()

        for thread in (self._video_thread, self._scheduler_thread):
            if thread is not None and thread.is_alive():
                thread.join(timeout=2.0)

        self._video_thread = None
        self._scheduler_thread = None
        self._log("demo player stopped")

    def _elapsed_locked(self) -> float:
        if self._state == "playing" and self._cycle_anchor is not None:
            return max(0.0, time.monotonic() - self._cycle_anchor)
        if self._state == "paused":
            return max(0.0, self._paused_t)
        return 0.0

    def _set_cycle_start(self) -> None:
        with self._state_lock:
            now = time.monotonic()
            self._cycle_anchor = now
            if self._state == "paused":
                self._paused_t = 0.0

    def _current_demo_time(self) -> float:
        with self._state_lock:
            return self._elapsed_locked()

    def _wait_until_running(self) -> bool:
        while not self._stop_event.is_set():
            if self._resume_event.wait(timeout=0.1):
                return True
        return False

    def _wait_until(self, target_seconds: float) -> bool:
        while not self._stop_event.is_set():
            if not self._wait_until_running():
                return False

            remaining = target_seconds - self._current_demo_time()
            if remaining <= 0:
                return True

            time.sleep(min(0.05, remaining))
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

            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
            frame_interval = 1.0 / fps if fps > 0 else 1.0 / 15.0

            while not self._stop_event.is_set():
                if not self._wait_until_running():
                    break

                ok, frame = capture.read()
                if not ok:
                    capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ok, frame = capture.read()
                    if not ok:
                        self._log("video loop hit EOF and failed to restart; retrying capture")
                        break

                try:
                    app_state.set_latest_frame(frame)
                except Exception as exc:
                    self._log(f"set_latest_frame failed: {exc}")

                if not self._sleep_with_control(frame_interval):
                    break

            capture.release()

    def _scheduler_loop(self) -> None:
        loop_count = 0
        while not self._stop_event.is_set():
            loop_count += 1
            self._set_cycle_start()

            for index, event in enumerate(self._events):
                if not self._wait_until(float(event["at"])):
                    return
                self._fire_event(index, event, loop_count)

            if self._stop_event.is_set():
                return

            self._log(f"scenario loop {loop_count} complete")

    def _fire_event(self, index: int, event: dict[str, Any], loop_count: int) -> None:
        event_type = str(event["type"])
        self._log(
            f"event loop={loop_count} index={index} at={event['at']:.1f}s type={event_type}"
        )

        try:
            if event_type == "seed":
                seed(include_medevac=False)
                return

            if event_type == "reset":
                app_state._reset_for_tests()
                return

            if event_type == "suggestion":
                casualty_id = str(event["casualty_id"])
                text = str(event["text"])
                if not text.startswith(f"{casualty_id}:"):
                    text = f"{casualty_id}: {text}"
                suggestion = AISuggestion(
                    timestamp=self._timestamp(),
                    source=str(event["source"]),
                    suggestion=text,
                    confidence=float(event["confidence"]),
                    accepted_by_medic=None,
                )
                app_state.add_suggestion(suggestion)
                return

            if event_type == "intervention":
                intervention = Intervention(
                    type=str(event["intervention_type"]),
                    location=str(event["location"]),
                    timestamp=self._timestamp(),
                    confirmed_by_medic=bool(event.get("confirmed_by_medic", True)),
                    source=str(event.get("source", "manual")),
                )
                app_state.add_intervention(str(event["casualty_id"]), intervention)
                return

            if event_type == "voice":
                app_state.set_voice_state(str(event["state"]), str(event.get("transcription", "")))
                return

            if event_type == "medevac":
                app_state.set_active_medevac(
                    str(event["casualty_id"]),
                    self._normalize_nine_line(event["nine_line"]),
                )
                return

            if event_type == "triage_update":
                category_name = str(event["triage_category"]).upper()
                if category_name in {"DECEASED", "EXPECTANT"}:
                    self._log(
                        f"warning: rejected prohibited triage_update {category_name} for {event['casualty_id']}"
                    )
                    return

                casualty = app_state.get_casualty(str(event["casualty_id"]))
                if casualty is None:
                    self._log(f"warning: casualty {event['casualty_id']} not found for triage_update")
                    return

                casualty.triage_category = TriageCategory[category_name]
                casualty.triage_confirmed_by_medic = True
                app_state.upsert_casualty(casualty)
                return

            self._log(f"warning: unsupported event type {event_type}")
        except Exception as exc:
            self._log(f"event index {index} failed: {exc}")

    def _load_scenario(self, path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DemoPlayerError(f"Malformed demo script JSON: {exc}") from exc

        events = data.get("events")
        if not isinstance(events, list):
            raise DemoPlayerError("Demo script must contain an 'events' list")

        parsed_events: list[dict[str, Any]] = []
        for index, raw_event in enumerate(events):
            try:
                parsed_events.append(self._parse_event(index, raw_event))
            except Exception as exc:
                raise DemoPlayerError(f"Event {index} failed to parse: {exc}") from exc

        parsed_events.sort(key=lambda item: item["at"])
        return {
            "name": str(data.get("name", path.stem)),
            "description": str(data.get("description", "")),
            "events": parsed_events,
        }

    def _parse_event(self, index: int, raw_event: Any) -> dict[str, Any]:
        if not isinstance(raw_event, dict):
            raise ValueError("event must be an object")

        if "at" not in raw_event or "type" not in raw_event:
            raise ValueError("event must include 'at' and 'type'")

        event_type = str(raw_event["type"])
        at_seconds = float(raw_event["at"])
        if at_seconds < 0:
            raise ValueError("'at' must be non-negative")

        event = dict(raw_event)
        event["type"] = event_type
        event["at"] = at_seconds

        required_fields = {
            "suggestion": ("source", "casualty_id", "text", "confidence"),
            "intervention": ("casualty_id", "intervention_type", "location"),
            "voice": ("state",),
            "medevac": ("casualty_id", "nine_line"),
            "triage_update": ("casualty_id", "triage_category"),
        }
        if event_type in required_fields:
            missing = [field for field in required_fields[event_type] if field not in event]
            if missing:
                raise ValueError(f"missing required field(s): {', '.join(missing)}")

        if event_type not in {"seed", "reset", "suggestion", "intervention", "voice", "medevac", "triage_update"}:
            raise ValueError(f"unsupported event type: {event_type}")

        if event_type == "medevac" and not isinstance(event["nine_line"], dict):
            raise ValueError("'nine_line' must be an object")

        return event

    def _normalize_nine_line(self, raw: dict[str, Any]) -> dict[str, str]:
        if all(f"line_{index}" in raw for index in range(1, 10)):
            return {f"line_{index}": str(raw[f"line_{index}"]) for index in range(1, 10)}

        frequency = str(raw.get("frequency", "")).strip()
        callsign = str(raw.get("callsign", "")).strip()
        freq_and_callsign = " / ".join(part for part in (frequency, callsign) if part) or "awaiting input"

        mapped = {
            "line_1": str(raw.get("location", "awaiting input")),
            "line_2": freq_and_callsign,
            "line_3": str(raw.get("patients_by_precedence", "awaiting input")),
            "line_4": str(raw.get("special_equipment", "awaiting input")),
            "line_5": str(raw.get("patients_by_type", "awaiting input")),
            "line_6": str(raw.get("security", "awaiting input")),
            "line_7": str(raw.get("marking", "awaiting input")),
            "line_8": str(raw.get("nationality", "awaiting input")),
            "line_9": str(raw.get("nbc", "awaiting input")),
        }
        return mapped

    def _timestamp(self) -> datetime:
        return datetime.now(timezone.utc)

    def _log(self, message: str) -> None:
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        print(f"[{stamp}] demo_player: {message}", flush=True)
