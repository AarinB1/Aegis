from __future__ import annotations

import importlib
import inspect
from dataclasses import fields, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Sequence

from vision.integration import build_wound_suggestions, detected_wounds_from_analysis

REPO_ROOT = Path(__file__).resolve().parents[1]


def resolve_app_state() -> Any | None:
    if not (REPO_ROOT / "shared" / "state.py").exists():
        return None
    try:
        return importlib.import_module("shared.state").app_state
    except Exception:
        return None


def resolve_schema_module() -> Any | None:
    if not (REPO_ROOT / "schema.py").exists():
        return None
    try:
        return importlib.import_module("schema")
    except Exception:
        return None


class VisionStateBridge:
    def __init__(
        self,
        *,
        app_state: Any | None = None,
        casualty_factory: Callable[..., Any] | None = None,
        suggestion_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.app_state = app_state if app_state is not None else resolve_app_state()
        schema_module = resolve_schema_module()
        self.casualty_factory = casualty_factory or getattr(schema_module, "Casualty", None)
        self.suggestion_factory = suggestion_factory or getattr(schema_module, "Suggestion", None) or getattr(
            schema_module, "AISuggestion", None
        )
        self.wound_factory = getattr(schema_module, "Wound", None) if schema_module is not None else None
        self.triage_category = getattr(schema_module, "TriageCategory", None) if schema_module is not None else None
        self.respiratory_status = (
            getattr(schema_module, "RespiratoryStatus", None) if schema_module is not None else None
        )
        self._emitted_suggestion_ids: set[str] = set()

    def publish(
        self,
        *,
        casualties: Sequence[dict],
        latest_frame: Any,
    ) -> None:
        if self.app_state is None:
            return

        if hasattr(self.app_state, "set_latest_frame"):
            self.app_state.set_latest_frame(latest_frame)

        for casualty in casualties:
            casualty_obj = self._build_casualty(casualty)
            built_suggestions = self._build_suggestions(casualty["alias"], casualty["analysis"])
            pending_suggestions = [
                (suggestion_key, suggestion)
                for suggestion_key, suggestion in built_suggestions
                if suggestion_key not in self._emitted_suggestion_ids
            ]

            if casualty_obj is not None and hasattr(casualty_obj, "ai_suggestions_log"):
                casualty_obj.ai_suggestions_log.extend(
                    [suggestion for _, suggestion in pending_suggestions if suggestion is not None]
                )

            if casualty_obj is not None and hasattr(self.app_state, "upsert_casualty"):
                self.app_state.upsert_casualty(casualty_obj)

            if self.suggestion_factory is None or not hasattr(self.app_state, "add_suggestion"):
                continue

            for suggestion_key, suggestion in pending_suggestions:
                if suggestion is None:
                    continue
                self.app_state.add_suggestion(suggestion)
                self._emitted_suggestion_ids.add(suggestion_key)

    def reset(self) -> None:
        self._emitted_suggestion_ids.clear()

    def _build_casualty(self, casualty: dict) -> Any | None:
        if self.casualty_factory is None:
            return None

        casualty_fields = self._field_names(self.casualty_factory)
        existing = None
        if hasattr(self.app_state, "get_casualty"):
            try:
                existing = self.app_state.get_casualty(casualty["alias"])
            except Exception:
                existing = None

        wounds = [self._build_wound(wound) for wound in casualty["analysis"].get("wounds", [])]
        last_seen = datetime.fromtimestamp(casualty["last_seen_ts"])
        note_list = list(self._preserve(existing, "notes", []))
        values = {
            "id": casualty["alias"],
            "casualty_id": casualty["alias"],
            "track_id": casualty["track_id"],
            "reid_embedding": self._preserve(existing, "reid_embedding", None),
            "bbox": casualty["bbox"],
            "first_seen": self._preserve(existing, "first_seen", last_seen),
            "last_seen": last_seen,
            "triage_category": self._preserve(
                existing,
                "triage_category",
                self._default_triage_category(casualty_fields),
            ),
            "triage_confirmed_by_medic": self._preserve(existing, "triage_confirmed_by_medic", False),
            "triage_confidence": self._preserve(existing, "triage_confidence", 0.0),
            "wounds": wounds,
            "interventions": self._preserve(existing, "interventions", []),
            "respiratory_status": self._preserve(existing, "respiratory_status", self._default_respiratory_status()),
            "respiratory_rate": self._preserve(existing, "respiratory_rate", None),
            "respiratory_confidence": self._preserve(existing, "respiratory_confidence", 0.0),
            "last_seen_ts": casualty["last_seen_ts"],
            "notes": note_list,
            "medic_notes": self._preserve(existing, "medic_notes", "; ".join(note_list)),
            "posture": self._preserve(existing, "posture", "unknown"),
            "responsive": self._preserve(existing, "responsive", None),
            "march_checklist": self._preserve(
                existing,
                "march_checklist",
                {
                    "massive_hemorrhage": False,
                    "airway": False,
                    "respiration": False,
                    "circulation": False,
                    "hypothermia": False,
                },
            ),
            "ai_suggestions_log": self._preserve(existing, "ai_suggestions_log", []),
            "overall_severity": casualty["analysis"].get("overall_severity", 0.0),
        }
        return self._instantiate(self.casualty_factory, values)

    def _build_wound(self, wound: dict) -> Any:
        if self.wound_factory is None:
            return detected_wounds_from_analysis({"wounds": [wound]})[0]

        wound_fields = self._field_names(self.wound_factory)
        location = wound["location"]
        bbox = (
            int(location["x"]),
            int(location["y"]),
            int(location["x"] + location["width"]),
            int(location["y"] + location["height"]),
        )
        values = {
            "bbox": bbox,
            "location": wound.get("location_type", "limb"),
            "body_region": wound.get("location_type", "limb"),
            "location_type": wound.get("location_type", "limb"),
            "area_cm2": wound["size_cm2"],
            "severity": (
                self._severity_label(wound["severity"])
                if "area_cm2" in wound_fields and "active_bleeding" in wound_fields
                else wound["severity"]
            ),
            "type": wound["type"],
            "wound_type": wound["type"],
            "bleeding": wound["bleeding"],
            "active_bleeding": wound["bleeding"],
            "bleeding_detected": wound.get("bleeding_detected", wound["bleeding"]),
            "size_cm2": wound["size_cm2"],
            "confidence": wound["confidence"],
            "ai_confidence": wound["confidence"],
            "mask_png_path": None,
            "notes": wound.get("notes"),
        }
        built = self._instantiate(self.wound_factory, values)
        return built if built is not None else detected_wounds_from_analysis({"wounds": [wound]})[0]

    def _default_triage_category(self, casualty_fields: set[str] | None = None) -> Any:
        casualty_fields = casualty_fields or set()
        if "triage_confidence" in casualty_fields or "last_seen_ts" in casualty_fields:
            return "UNASSIGNED"
        if self.triage_category is None:
            return "UNASSIGNED"
        return (
            getattr(self.triage_category, "UNASSIGNED", None)
            or getattr(self.triage_category, "UNASSESSED", None)
            or "UNASSIGNED"
        )

    def _default_respiratory_status(self) -> Any:
        if self.respiratory_status is None:
            return "unknown"
        return getattr(self.respiratory_status, "UNKNOWN", "unknown")

    def _preserve(self, existing: Any, field_name: str, default: Any) -> Any:
        if existing is None:
            return default
        return getattr(existing, field_name, default)

    def _build_suggestions(self, casualty_id: str, analysis: dict) -> list[tuple[str, Any]]:
        if self.suggestion_factory is None:
            return []

        suggestion_fields = self._field_names(self.suggestion_factory)
        if {"field", "proposed_value", "ts"}.issubset(suggestion_fields):
            return [
                (getattr(suggestion, "id", f"{casualty_id}-vision-suggestion-{index}"), suggestion)
                for index, suggestion in enumerate(
                    build_wound_suggestions(casualty_id, analysis, self.suggestion_factory),
                    start=1,
                )
            ]

        wounds = detected_wounds_from_analysis(analysis)
        if {"kind", "payload", "created_at"}.issubset(suggestion_fields):
            created_at = datetime.now()
            suggestions = []
            for index, wound in enumerate(wounds, start=1):
                suggestion_key = f"{casualty_id}-vision-wound-{index}"
                suggestion = self._instantiate(
                    self.suggestion_factory,
                    {
                        "id": suggestion_key,
                        "source": "vision",
                        "casualty_id": casualty_id,
                        "kind": "wound_detected",
                        "payload": {
                            "bbox": wound.bbox,
                            "wound_type": wound.wound_type,
                            "location_type": wound.location_type,
                            "bleeding": wound.bleeding,
                            "size_cm2": wound.size_cm2,
                            "severity": wound.severity,
                            "confidence": wound.confidence,
                        },
                        "confidence": wound.confidence,
                        "created_at": created_at,
                        "status": "pending",
                    },
                )
                suggestions.append((suggestion_key, suggestion))
            return suggestions

        if {"timestamp", "suggestion", "accepted_by_medic"}.issubset(suggestion_fields):
            created_at = datetime.now()
            suggestions = []
            for index, wound in enumerate(wounds, start=1):
                suggestion_key = f"{casualty_id}-vision-ai-log-{index}"
                suggestion = self._instantiate(
                    self.suggestion_factory,
                    {
                        "timestamp": created_at,
                        "source": "vision",
                        "suggestion": self._ai_suggestion_text(casualty_id, wound),
                        "confidence": wound.confidence,
                        "accepted_by_medic": None,
                    },
                )
                suggestions.append((suggestion_key, suggestion))
            return suggestions

        return []

    def _severity_label(self, severity: float) -> str:
        if severity >= 0.75:
            return "severe"
        if severity >= 0.4:
            return "moderate"
        return "minor"

    def _ai_suggestion_text(self, casualty_id: str, wound: Any) -> str:
        bleeding_text = "bleeding" if wound.bleeding else "non-bleeding"
        return (
            f"{casualty_id}: {bleeding_text} {wound.location_type} {wound.wound_type} "
            f"(severity {wound.severity:.2f}, size {wound.size_cm2:.1f} cm^2)"
        )

    def _field_names(self, factory: Callable[..., Any]) -> set[str]:
        try:
            if is_dataclass(factory):
                return {field.name for field in fields(factory)}
            if inspect.isclass(factory) and is_dataclass(factory):
                return {field.name for field in fields(factory)}
            return set(inspect.signature(factory).parameters)
        except Exception:
            return set()

    def _instantiate(self, factory: Callable[..., Any], values: dict[str, Any]) -> Any | None:
        allowed = self._field_names(factory)
        if not allowed:
            try:
                return factory(**values)
            except Exception:
                return None

        filtered = {key: value for key, value in values.items() if key in allowed}
        try:
            return factory(**filtered)
        except Exception:
            return None
