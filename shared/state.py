from __future__ import annotations

import copy
import threading
from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import numpy as np

from schema import AISuggestion, Casualty, Intervention


@dataclass
class AuditEntry:
    timestamp: datetime
    source: str
    action: str
    details: dict[str, Any]


@dataclass
class PendingSuggestion:
    id: str
    casualty_id: str | None
    source: str
    confidence: float
    created_at: datetime
    status: str
    raw: Any


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
        self._suggestions: dict[str, PendingSuggestion] = {}
        self._interventions: dict[str, list[Intervention]] = {}
        self._active_medevac: dict[str, Any] | None = None
        self._latest_frame: np.ndarray | None = None
        self._voice_state: tuple[str, str] = ("idle", "")
        self._audit_log: list[AuditEntry] = []
        self._ai_enabled = True
        self._initialized = True

    def upsert_casualty(self, casualty: Casualty) -> None:
        casualty_id = self._casualty_id(casualty)
        if casualty_id is None:
            raise ValueError("casualty must expose casualty_id or id")

        with self._lock:
            self._casualties[casualty_id] = copy.deepcopy(casualty)
            self.audit(
                "state",
                "upsert_casualty",
                {
                    "casualty_id": casualty_id,
                    "triage_category": self._safe_attr(casualty, "triage_category"),
                },
            )

    def add_suggestion(self, suggestion: Any) -> str:
        with self._lock:
            stored = PendingSuggestion(
                id=self._suggestion_id(suggestion),
                casualty_id=self._suggestion_casualty_id(suggestion),
                source=str(self._safe_attr(suggestion, "source", "unknown")),
                confidence=float(self._safe_attr(suggestion, "confidence", 0.0) or 0.0),
                created_at=self._suggestion_timestamp(suggestion),
                status="pending",
                raw=copy.deepcopy(suggestion),
            )
            self._suggestions[stored.id] = stored
            self.audit(
                "state",
                "add_suggestion",
                {
                    "suggestion_id": stored.id,
                    "casualty_id": stored.casualty_id,
                    "source": stored.source,
                },
            )
            return stored.id

    def add_intervention(self, casualty_id: str, intervention: Intervention) -> None:
        with self._lock:
            stored = copy.deepcopy(intervention)
            self._interventions.setdefault(casualty_id, []).append(stored)

            casualty = self._casualties.get(casualty_id)
            if casualty is not None:
                updated = copy.deepcopy(casualty)
                updated.interventions.append(stored)
                self._casualties[casualty_id] = updated

            self.audit(
                "state",
                "add_intervention",
                {
                    "casualty_id": casualty_id,
                    "type": self._safe_attr(stored, "type"),
                    "location": self._safe_attr(stored, "location"),
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

    def get_active_medevac(self) -> dict[str, Any] | None:
        with self._lock:
            active = self._active_medevac
        return copy.deepcopy(active)

    def set_latest_frame(self, frame: np.ndarray | None) -> None:
        with self._lock:
            self._latest_frame = None if frame is None else frame.copy()
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
            self._audit_log.append(
                AuditEntry(
                    timestamp=self._timestamp(),
                    source=source,
                    action=action,
                    details=copy.deepcopy(details),
                )
            )
            overflow = len(self._audit_log) - self._MAX_AUDIT_ENTRIES
            if overflow > 0:
                del self._audit_log[:overflow]

    def get_roster(self) -> list[Casualty]:
        with self._lock:
            roster = list(self._casualties.values())
        return copy.deepcopy(roster)

    def get_casualty(self, casualty_id: str) -> Casualty | None:
        with self._lock:
            casualty = self._casualties.get(casualty_id)
        return None if casualty is None else copy.deepcopy(casualty)

    def get_pending_suggestions(self) -> list[PendingSuggestion]:
        with self._lock:
            suggestions = [
                suggestion for suggestion in self._suggestions.values() if suggestion.status == "pending"
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

    def set_ai_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._ai_enabled = enabled
            self.audit("medic", "set_ai_enabled", {"enabled": enabled})

    def confirm_suggestion(self, suggestion_id: str) -> PendingSuggestion | None:
        return self._set_suggestion_status(suggestion_id, status="confirmed", accepted_by_medic=True)

    def dismiss_suggestion(self, suggestion_id: str) -> PendingSuggestion | None:
        return self._set_suggestion_status(suggestion_id, status="dismissed", accepted_by_medic=False)

    def _set_suggestion_status(
        self,
        suggestion_id: str,
        *,
        status: str,
        accepted_by_medic: bool,
    ) -> PendingSuggestion | None:
        with self._lock:
            current = self._suggestions.get(suggestion_id)
            if current is None:
                return None

            updated_raw = self._update_raw_suggestion(current.raw, status=status, accepted_by_medic=accepted_by_medic)
            updated = PendingSuggestion(
                id=current.id,
                casualty_id=current.casualty_id,
                source=current.source,
                confidence=current.confidence,
                created_at=current.created_at,
                status=status,
                raw=updated_raw,
            )
            self._suggestions[suggestion_id] = updated
            self.audit(
                "medic",
                f"{status}_suggestion",
                {
                    "suggestion_id": suggestion_id,
                    "casualty_id": current.casualty_id,
                    "source": current.source,
                },
            )
        return copy.deepcopy(updated)

    def _update_raw_suggestion(self, raw: Any, *, status: str, accepted_by_medic: bool) -> Any:
        copied = copy.deepcopy(raw)
        if isinstance(copied, AISuggestion):
            return replace(copied, accepted_by_medic=accepted_by_medic)

        dataclass_fields = self._field_names(type(copied)) if is_dataclass(copied) else set()
        replace_values: dict[str, Any] = {}
        if "status" in dataclass_fields:
            replace_values["status"] = status
        if "accepted_by_medic" in dataclass_fields:
            replace_values["accepted_by_medic"] = accepted_by_medic
        if replace_values:
            return replace(copied, **replace_values)

        if hasattr(copied, "status"):
            try:
                setattr(copied, "status", status)
            except Exception:
                pass
        if hasattr(copied, "accepted_by_medic"):
            try:
                setattr(copied, "accepted_by_medic", accepted_by_medic)
            except Exception:
                pass
        return copied

    def _casualty_id(self, casualty: Any) -> str | None:
        return self._safe_attr(casualty, "casualty_id") or self._safe_attr(casualty, "id")

    def _suggestion_id(self, suggestion: Any) -> str:
        return str(self._safe_attr(suggestion, "id", str(uuid4())))

    def _suggestion_casualty_id(self, suggestion: Any) -> str | None:
        casualty_id = self._safe_attr(suggestion, "casualty_id")
        if casualty_id is not None:
            return str(casualty_id)

        text = self._safe_attr(suggestion, "suggestion")
        if isinstance(text, str) and ":" in text:
            return text.split(":", 1)[0].strip() or None
        return None

    def _suggestion_timestamp(self, suggestion: Any) -> datetime:
        ts = self._safe_attr(suggestion, "timestamp") or self._safe_attr(suggestion, "created_at")
        if isinstance(ts, datetime):
            return ts
        return self._timestamp()

    def _safe_attr(self, obj: Any, name: str, default: Any = None) -> Any:
        return getattr(obj, name, default)

    def _field_names(self, factory: type[Any]) -> set[str]:
        if is_dataclass(factory):
            return {field.name for field in fields(factory)}
        return set()

    def _reset_for_tests(self) -> None:
        with self._lock:
            self._casualties.clear()
            self._suggestions.clear()
            self._interventions.clear()
            self._active_medevac = None
            self._latest_frame = None
            self._voice_state = ("idle", "")
            self._audit_log.clear()
            self._ai_enabled = True

    @staticmethod
    def _timestamp() -> datetime:
        return datetime.now(timezone.utc)


app_state = AppState()
