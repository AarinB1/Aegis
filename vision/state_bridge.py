from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from dataclasses import fields, is_dataclass
from typing import Any, Callable, Iterable, Sequence

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
        self.suggestion_factory = suggestion_factory or getattr(schema_module, "Suggestion", None)
        self.wound_factory = getattr(schema_module, "Wound", None) if schema_module is not None else None
        self.triage_category = getattr(schema_module, "TriageCategory", None) if schema_module is not None else None
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
            if casualty_obj is not None and hasattr(self.app_state, "upsert_casualty"):
                self.app_state.upsert_casualty(casualty_obj)

            if self.suggestion_factory is None or not hasattr(self.app_state, "add_suggestion"):
                continue

            for suggestion in build_wound_suggestions(
                casualty["alias"],
                casualty["analysis"],
                self.suggestion_factory,
            ):
                if suggestion.id in self._emitted_suggestion_ids:
                    continue
                self.app_state.add_suggestion(suggestion)
                self._emitted_suggestion_ids.add(suggestion.id)

    def reset(self) -> None:
        self._emitted_suggestion_ids.clear()

    def _build_casualty(self, casualty: dict) -> Any | None:
        if self.casualty_factory is None:
            return None

        existing = None
        if hasattr(self.app_state, "get_casualty"):
            try:
                existing = self.app_state.get_casualty(casualty["alias"])
            except Exception:
                existing = None

        wounds = [self._build_wound(wound) for wound in casualty["analysis"].get("wounds", [])]
        values = {
            "id": casualty["alias"],
            "track_id": casualty["track_id"],
            "bbox": casualty["bbox"],
            "triage_category": self._preserve(existing, "triage_category", self._default_triage_category()),
            "triage_confidence": self._preserve(existing, "triage_confidence", 0.0),
            "wounds": wounds,
            "interventions": self._preserve(existing, "interventions", []),
            "respiratory_status": self._preserve(existing, "respiratory_status", "unknown"),
            "respiratory_confidence": self._preserve(existing, "respiratory_confidence", 0.0),
            "last_seen_ts": casualty["last_seen_ts"],
            "notes": self._preserve(existing, "notes", []),
        }
        return self._instantiate(self.casualty_factory, values)

    def _build_wound(self, wound: dict) -> Any:
        if self.wound_factory is None:
            location = wound["location"]
            return detected_wounds_from_analysis({"wounds": [wound]})[0]

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
            "location_type": wound.get("location_type", "limb"),
            "severity": wound["severity"],
            "type": wound["type"],
            "wound_type": wound["type"],
            "bleeding": wound["bleeding"],
            "bleeding_detected": wound.get("bleeding_detected", wound["bleeding"]),
            "size_cm2": wound["size_cm2"],
            "confidence": wound["confidence"],
            "notes": wound.get("notes"),
        }
        built = self._instantiate(self.wound_factory, values)
        return built if built is not None else detected_wounds_from_analysis({"wounds": [wound]})[0]

    def _default_triage_category(self) -> Any:
        if self.triage_category is None:
            return "UNASSIGNED"
        return getattr(self.triage_category, "UNASSIGNED", "UNASSIGNED")

    def _preserve(self, existing: Any, field_name: str, default: Any) -> Any:
        if existing is None:
            return default
        return getattr(existing, field_name, default)

    def _instantiate(self, factory: Callable[..., Any], values: dict[str, Any]) -> Any | None:
        try:
            if is_dataclass(factory):
                allowed = {field.name for field in fields(factory)}
            elif inspect.isclass(factory) and is_dataclass(factory):
                allowed = {field.name for field in fields(factory)}
            else:
                allowed = set(inspect.signature(factory).parameters)
        except Exception:
            try:
                return factory(**values)
            except Exception:
                return None

        filtered = {key: value for key, value in values.items() if key in allowed}
        try:
            return factory(**filtered)
        except Exception:
            return None
