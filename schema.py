from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4


BBox = tuple[int, int, int, int]
BodyRegion = Literal["head", "torso", "limb"]
SuggestionSource = Literal["vision", "audio", "triage"]
SuggestionStatus = Literal["pending", "confirmed", "dismissed"]
InterventionSource = Literal["voice", "manual"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid4())


def _validate_bbox(bbox: BBox) -> None:
    if len(bbox) != 4:
        raise ValueError("bbox must contain exactly four integers")

    if not all(isinstance(value, int) for value in bbox):
        raise ValueError("bbox values must be integers")


def _is_black_priority(value: Any) -> bool:
    if isinstance(value, TriageCategory):
        return value is TriageCategory.BLACK

    if isinstance(value, str):
        return value.strip().upper() == TriageCategory.BLACK.value

    return False


def _payload_contains_black_priority(payload: Any) -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_name = str(key).lower()
            if ("priority" in key_name or "triage" in key_name) and _is_black_priority(value):
                return True

            if _payload_contains_black_priority(value):
                return True

    elif isinstance(payload, (list, tuple, set)):
        for item in payload:
            if _payload_contains_black_priority(item):
                return True

    return False


class TriageCategory(Enum):
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"
    BLACK = "BLACK"
    UNASSIGNED = "UNASSIGNED"


@dataclass(kw_only=True)
class Wound:
    bbox: BBox
    wound_type: str
    body_region: BodyRegion
    bleeding: bool
    size_cm2: float
    confidence: float
    severity: float

    def __post_init__(self) -> None:
        _validate_bbox(self.bbox)

        if self.body_region not in {"head", "torso", "limb"}:
            raise ValueError("body_region must be one of: head, torso, limb")

        if not 0.0 <= self.severity <= 1.0:
            raise ValueError("severity must be between 0.0 and 1.0")


@dataclass(kw_only=True)
class Casualty:
    id: str
    track_id: int | None = None
    bbox: BBox
    last_seen: datetime
    wounds: list[Wound] = field(default_factory=list)
    triage: TriageCategory = TriageCategory.UNASSIGNED
    overall_severity: float
    notes: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        _validate_bbox(self.bbox)


@dataclass(kw_only=True)
class Suggestion:
    id: str = field(default_factory=_new_id)
    source: SuggestionSource
    casualty_id: str
    kind: str
    payload: dict[str, Any]
    confidence: float
    created_at: datetime = field(default_factory=_utcnow)
    status: SuggestionStatus = "pending"

    def __post_init__(self) -> None:
        if _payload_contains_black_priority(self.payload):
            raise ValueError("automatic BLACK triage suggestions are not allowed")


@dataclass(kw_only=True)
class Intervention:
    id: str = field(default_factory=_new_id)
    casualty_id: str
    kind: str
    location: str | None
    notes: str
    timestamp: datetime
    source: InterventionSource


@dataclass(kw_only=True)
class AuditEntry:
    timestamp: datetime
    source: str
    action: str
    details: dict[str, Any]
