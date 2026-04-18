from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, List, Sequence


@dataclass(frozen=True)
class DetectedWound:
    bbox: tuple[int, int, int, int]
    severity: float
    wound_type: str
    location_type: str
    bleeding: bool
    size_cm2: float
    confidence: float
    notes: str | None = None

    @property
    def bleeding_detected(self) -> bool:
        return self.bleeding

    @property
    def type(self) -> str:
        return self.wound_type

    @property
    def location(self) -> str:
        return self.location_type


def detected_wounds_from_analysis(analysis: dict) -> list[DetectedWound]:
    wounds: list[DetectedWound] = []
    for wound in analysis.get("wounds", []):
        location = wound["location"]
        x1 = int(location["x"])
        y1 = int(location["y"])
        x2 = x1 + int(location["width"])
        y2 = y1 + int(location["height"])
        wounds.append(
            DetectedWound(
                bbox=(x1, y1, x2, y2),
                severity=float(wound["severity"]),
                wound_type=str(wound["type"]),
                location_type=str(wound.get("location_type", "limb")),
                bleeding=bool(wound["bleeding"]),
                size_cm2=float(wound["size_cm2"]),
                confidence=float(wound["confidence"]),
                notes=wound.get("notes"),
            )
        )
    return wounds


def build_wound_suggestions(
    casualty_id: str,
    analysis: dict,
    suggestion_factory: Callable[..., Any],
    *,
    now_ts: float | None = None,
) -> list[Any]:
    created_at = now_ts if now_ts is not None else time.time()
    suggestions: list[Any] = []
    for index, wound in enumerate(detected_wounds_from_analysis(analysis), start=1):
        suggestions.append(
            suggestion_factory(
                id=f"{casualty_id}-vision-wound-{index}",
                casualty_id=casualty_id,
                source="vision",
                field="wound",
                proposed_value=wound,
                confidence=wound.confidence,
                ts=created_at,
                rationale=_format_wound_rationale(wound),
            )
        )
    return suggestions


def top_wound_suggestion(
    casualty_id: str,
    analysis: dict,
    suggestion_factory: Callable[..., Any],
    *,
    now_ts: float | None = None,
) -> Any | None:
    wounds = sorted(
        detected_wounds_from_analysis(analysis),
        key=lambda wound: (wound.bleeding, wound.severity, wound.size_cm2),
        reverse=True,
    )
    if not wounds:
        return None

    created_at = now_ts if now_ts is not None else time.time()
    wound = wounds[0]
    return suggestion_factory(
        id=f"{casualty_id}-vision-top-wound",
        casualty_id=casualty_id,
        source="vision",
        field="wound",
        proposed_value=wound,
        confidence=wound.confidence,
        ts=created_at,
        rationale=_format_wound_rationale(wound),
    )


def _format_wound_rationale(wound: DetectedWound) -> str:
    bleeding_text = "bleeding" if wound.bleeding else "non-bleeding"
    return (
        f"Detected {bleeding_text} {wound.location_type} {wound.wound_type} "
        f"(severity {wound.severity:.2f}, size {wound.size_cm2:.1f} cm2)"
    )
