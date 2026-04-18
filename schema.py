# schema.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class TriageCategory(Enum):
    IMMEDIATE = "red"       # Life-threatening, salvageable
    DELAYED = "yellow"      # Serious but stable
    MINIMAL = "green"       # Walking wounded
    EXPECTANT = "gray"      # Unlikely to survive given resources
    DECEASED = "black"      # Medic-confirmed only
    UNASSESSED = "white"    # Default


class RespiratoryStatus(Enum):
    NORMAL = "normal"
    STRIDOR = "stridor"
    GURGLING = "gurgling"
    AGONAL = "agonal"
    ABSENT = "absent"
    UNKNOWN = "unknown"


@dataclass
class Wound:
    location: str                              # "left_thigh", "chest", etc.
    area_cm2: float
    severity: str                              # "minor", "moderate", "severe"
    active_bleeding: bool
    mask_png_path: Optional[str] = None
    ai_confidence: float = 0.0


@dataclass
class Intervention:
    type: str                                  # "tourniquet", "chest_seal", "npa", "pressure_dressing"
    location: str
    timestamp: datetime = field(default_factory=datetime.now)
    confirmed_by_medic: bool = True
    source: str = "manual"                     # "voice_command", "vision_detected", "manual"


@dataclass
class AISuggestion:
    """Single entry in a casualty's AI suggestion audit log."""
    timestamp: datetime
    source: str                                # "vision", "audio", "fusion"
    suggestion: str                            # human-readable
    confidence: float
    accepted_by_medic: Optional[bool] = None   # None = pending, True/False once acted on


@dataclass
class Casualty:
    casualty_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    reid_embedding: Optional[list] = None
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    triage_category: TriageCategory = TriageCategory.UNASSESSED
    triage_confirmed_by_medic: bool = False
    posture: str = "unknown"                   # "walking", "standing", "sitting", "prone", "supine"
    responsive: Optional[bool] = None
    wounds: list[Wound] = field(default_factory=list)
    respiratory_status: RespiratoryStatus = RespiratoryStatus.UNKNOWN
    respiratory_rate: Optional[int] = None
    interventions: list[Intervention] = field(default_factory=list)
    medic_notes: str = ""
    march_checklist: dict = field(default_factory=lambda: {
        "massive_hemorrhage": False,
        "airway": False,
        "respiration": False,
        "circulation": False,
        "hypothermia": False,
    })
    ai_suggestions_log: list[AISuggestion] = field(default_factory=list)


if __name__ == "__main__":
    example = Casualty(
        triage_category=TriageCategory.IMMEDIATE,
        triage_confirmed_by_medic=True,
        posture="supine",
        responsive=True,
        respiratory_status=RespiratoryStatus.STRIDOR,
        respiratory_rate=28,
        medic_notes="Penetrating wound R thigh; arterial bleed controlled.",
        wounds=[
            Wound(
                location="right_thigh",
                area_cm2=8.2,
                severity="severe",
                active_bleeding=False,
                ai_confidence=0.87,
            ),
        ],
        interventions=[
            Intervention(
                type="tourniquet",
                location="right_thigh_proximal",
                source="voice_command",
            ),
        ],
    )
    example.march_checklist["massive_hemorrhage"] = True

    print(example)
