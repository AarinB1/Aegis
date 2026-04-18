from __future__ import annotations

import copy
import threading
from dataclasses import replace
from typing import Any

import numpy as np

from schema import AuditEntry, Casualty, Intervention, Suggestion


class AppState:
    _instance: "AppState | None" = None
    _instance_lock = threading.Lock()
    _MAX_AUDIT_ENTRIES = 10_000

    def __new__(cls) -> "AppState":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._lock = threading.RLock()
        self._casualties: dict[str, Casualty] = {}
        self._suggestions: dict[str, Suggestion] = {}
        self._interventions: dict[str, list[Intervention]] = {}
        self._active_medevac: dict[str, Any] | None = None
        self._latest_frame: np.ndarray | None = None
        self._voice_state: tuple[str, str] = ("idle", "")
        self._audit_log: list[AuditEntry] = []
        self._ai_enabled = True
        self._initialized = True

    def upsert_casualty(self, casualty: Casualty) -> None:
        with self._lock:
            self._casualties[casualty.id] = copy.deepcopy(casualty)
            self.audit(
                "state",
                "upsert_casualty",
                {
                    "casualty_id": casualty.id,
                    "track_id": casualty.track_id,
                    "triage": casualty.triage.value,
                },
            )

    def add_suggestion(self, suggestion: Suggestion) -> str:
        with self._lock:
            stored = copy.deepcopy(suggestion)
            self._suggestions[stored.id] = stored
            self.audit(
                "state",
                "add_suggestion",
                {
                    "suggestion_id": stored.id,
                    "casualty_id": stored.casualty_id,
                    "kind": stored.kind,
                    "source": stored.source,
                },
            )
            return stored.id

    def add_intervention(self, casualty_id: str, intervention: Intervention) -> None:
        with self._lock:
            stored = copy.deepcopy(intervention)
            self._interventions.setdefault(casualty_id, []).append(stored)
            self.audit(
                "state",
                "add_intervention",
                {
                    "casualty_id": casualty_id,
                    "intervention_id": stored.id,
                    "kind": stored.kind,
                    "source": stored.source,
                },
            )

    def set_active_medevac(self, casualty_id: str, nine_line: dict[str, Any]) -> None:
        with self._lock:
            self._active_medevac = {
                "casualty_id": casualty_id,
                "nine_line": copy.deepcopy(nine_line),
            }
            self.audit(
                "state",
                "set_active_medevac",
                {"casualty_id": casualty_id, "fields": sorted(nine_line.keys())},
            )

    def set_latest_frame(self, frame: np.ndarray | None) -> None:
        with self._lock:
            self._latest_frame = frame
            self.audit(
                "state",
                "set_latest_frame",
                {
                    "has_frame": frame is not None,
                    "shape": list(frame.shape) if frame is not None else None,
                },
            )

    def set_voice_state(self, state: str, transcription: str) -> None:
        with self._lock:
            self._voice_state = (state, transcription)
            self.audit(
                "state",
                "set_voice_state",
                {"state": state, "has_transcription": bool(transcription)},
            )

    def audit(self, source: str, action: str, details: dict[str, Any]) -> None:
        with self._lock:
            entry = AuditEntry(
                timestamp=self._timestamp(),
                source=source,
                action=action,
                details=copy.deepcopy(details),
            )
            self._audit_log.append(entry)
            overflow = len(self._audit_log) - self._MAX_AUDIT_ENTRIES
            if overflow > 0:
                del self._audit_log[:overflow]

    def get_roster(self) -> list[Casualty]:
        with self._lock:
            roster = list(self._casualties.values())
        return copy.deepcopy(roster)

    def get_casualty(self, id: str) -> Casualty | None:
        with self._lock:
            casualty = self._casualties.get(id)
        return None if casualty is None else copy.deepcopy(casualty)

    def get_pending_suggestions(self) -> list[Suggestion]:
        with self._lock:
            suggestions = [
                suggestion
                for suggestion in self._suggestions.values()
                if suggestion.status == "pending"
            ]
        return copy.deepcopy(suggestions)

    def get_latest_frame(self) -> np.ndarray | None:
        with self._lock:
            frame = self._latest_frame
        return None if frame is None else frame.copy()

    def get_voice_state(self) -> tuple[str, str]:
        with self._lock:
            voice_state = self._voice_state
        return tuple(voice_state)

    def get_audit_log(self) -> list[AuditEntry]:
        with self._lock:
            audit_log = list(self._audit_log)
        return copy.deepcopy(audit_log)

    def is_ai_enabled(self) -> bool:
        with self._lock:
            enabled = self._ai_enabled
        return enabled

    def confirm_suggestion(self, id: str) -> Suggestion | None:
        with self._lock:
            suggestion = self._suggestions.get(id)
            if suggestion is None:
                return None

            updated = replace(suggestion, status="confirmed")
            self._suggestions[id] = updated
            self.audit(
                "medic",
                "confirm_suggestion",
                {
                    "suggestion_id": id,
                    "casualty_id": updated.casualty_id,
                    "previous_status": suggestion.status,
                    "new_status": updated.status,
                },
            )

        return copy.deepcopy(updated)

    def dismiss_suggestion(self, id: str) -> Suggestion | None:
        with self._lock:
            suggestion = self._suggestions.get(id)
            if suggestion is None:
                return None

            updated = replace(suggestion, status="dismissed")
            self._suggestions[id] = updated
            self.audit(
                "medic",
                "dismiss_suggestion",
                {
                    "suggestion_id": id,
                    "casualty_id": updated.casualty_id,
                    "previous_status": suggestion.status,
                    "new_status": updated.status,
                },
            )

        return copy.deepcopy(updated)

    def set_ai_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._ai_enabled = enabled
            self.audit(
                "medic",
                "set_ai_enabled",
                {"enabled": enabled},
            )

    @staticmethod
    def _timestamp():
        from datetime import datetime, timezone

        return datetime.now(timezone.utc)


app_state = AppState()
