from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from schema import AISuggestion, Casualty, Intervention, RespiratoryStatus, TriageCategory, Wound
from shared.state import app_state


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _build_demo_frame() -> np.ndarray:
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame[:, :, 1] = np.linspace(16, 42, frame.shape[1], dtype=np.uint8)
    frame[:, :, 2] = np.linspace(8, 30, frame.shape[0], dtype=np.uint8)[:, None]
    frame[70:650, 110:1170, :] += 10

    frame[120:260, 180:360, 2] = 210
    frame[120:260, 180:360, 1] = 45

    frame[250:430, 520:760, 2] = 185
    frame[250:430, 520:760, 1] = 155

    frame[390:560, 870:1080, 0] = 70
    frame[390:560, 870:1080, 1] = 75
    frame[390:560, 870:1080, 2] = 75

    frame[160:560, 638:642, :] = 140
    frame[358:362, 300:980, :] = 140
    return frame


def _immediate_casualty(now: datetime) -> Casualty:
    return Casualty(
        casualty_id="A1",
        first_seen=now - timedelta(minutes=9),
        last_seen=now - timedelta(seconds=11),
        triage_category=TriageCategory.IMMEDIATE,
        triage_confirmed_by_medic=True,
        posture="supine",
        responsive=True,
        wounds=[
            Wound(
                location="right_thigh",
                area_cm2=11.4,
                severity="severe",
                active_bleeding=False,
                ai_confidence=0.93,
            ),
            Wound(
                location="right_forearm",
                area_cm2=4.1,
                severity="moderate",
                active_bleeding=False,
                ai_confidence=0.71,
            ),
        ],
        respiratory_status=RespiratoryStatus.NORMAL,
        respiratory_rate=22,
        medic_notes="Tourniquet high on right thigh. Alert and following commands.",
        march_checklist={
            "massive_hemorrhage": True,
            "airway": True,
            "respiration": True,
            "circulation": True,
            "hypothermia": False,
        },
        ai_suggestions_log=[
            AISuggestion(
                timestamp=now - timedelta(minutes=6),
                source="vision",
                suggestion="A1: Severe right thigh hemorrhage with likely immediate evacuation need.",
                confidence=0.93,
                accepted_by_medic=True,
            )
        ],
    )


def _delayed_casualty(now: datetime) -> Casualty:
    return Casualty(
        casualty_id="A2",
        first_seen=now - timedelta(minutes=8),
        last_seen=now - timedelta(seconds=20),
        triage_category=TriageCategory.DELAYED,
        triage_confirmed_by_medic=False,
        posture="sitting",
        responsive=True,
        wounds=[
            Wound(
                location="left_chest",
                area_cm2=6.3,
                severity="moderate",
                active_bleeding=True,
                ai_confidence=0.82,
            )
        ],
        respiratory_status=RespiratoryStatus.NORMAL,
        respiratory_rate=26,
        medic_notes="Chest wound dressed. Speaking full sentences but guarded respirations.",
        march_checklist={
            "massive_hemorrhage": True,
            "airway": True,
            "respiration": False,
            "circulation": False,
            "hypothermia": False,
        },
        ai_suggestions_log=[
            AISuggestion(
                timestamp=now - timedelta(minutes=4),
                source="fusion",
                suggestion="A2: Delayed triage remains appropriate; monitor respiration closely.",
                confidence=0.77,
                accepted_by_medic=None,
            )
        ],
    )


def _unassessed_casualty(now: datetime) -> Casualty:
    return Casualty(
        casualty_id="A3",
        first_seen=now - timedelta(minutes=5),
        last_seen=now - timedelta(seconds=9),
        triage_category=TriageCategory.UNASSESSED,
        triage_confirmed_by_medic=False,
        posture="prone",
        responsive=None,
        wounds=[
            Wound(
                location="scalp",
                area_cm2=2.2,
                severity="minor",
                active_bleeding=False,
                ai_confidence=0.58,
            )
        ],
        respiratory_status=RespiratoryStatus.UNKNOWN,
        respiratory_rate=None,
        medic_notes="Needs manual assessment after current immediate cases.",
        march_checklist={
            "massive_hemorrhage": False,
            "airway": False,
            "respiration": False,
            "circulation": False,
            "hypothermia": False,
        },
        ai_suggestions_log=[],
    )


def seed() -> None:
    now = _now()

    app_state.upsert_casualty(_immediate_casualty(now))
    app_state.upsert_casualty(_delayed_casualty(now))
    app_state.upsert_casualty(_unassessed_casualty(now))

    app_state.add_intervention(
        "A1",
        Intervention(
            type="tourniquet",
            location="right_thigh_proximal",
            timestamp=now - timedelta(minutes=3),
            confirmed_by_medic=True,
            source="manual",
        ),
    )
    app_state.add_intervention(
        "A2",
        Intervention(
            type="pressure_dressing",
            location="left_chest",
            timestamp=now - timedelta(minutes=2),
            confirmed_by_medic=True,
            source="manual",
        ),
    )

    app_state.add_suggestion(
        AISuggestion(
            timestamp=now - timedelta(seconds=55),
            source="vision",
            suggestion="A2: Vision flags chest wound expansion; consider respiration reassessment.",
            confidence=0.81,
            accepted_by_medic=None,
        )
    )
    app_state.add_suggestion(
        AISuggestion(
            timestamp=now - timedelta(seconds=24),
            source="audio",
            suggestion="A3: Audio detected weak verbal response nearby; prioritize manual check.",
            confidence=0.66,
            accepted_by_medic=None,
        )
    )

    app_state.set_latest_frame(_build_demo_frame())
    app_state.set_active_medevac(
        "A1",
        {
            "line_1": "38S MB 4421 9912",
            "line_2": "31.40 secure",
            "line_3": "1 urgent, 1 priority",
            "line_4": "None",
            "line_5": "2 litter",
            "line_6": "Enemy nearby",
            "line_7": "Smoke",
            "line_8": "2 US military",
            "line_9": "Open field west of compound",
        },
    )
    app_state.audit("demo", "seed_fake_data", {"casualties": 3, "pending_suggestions": 2})
    app_state.audit("ui", "set_demo_mode", {"mode": "Fake"})
    app_state.set_voice_state("idle", "")


def reset_and_seed() -> None:
    app_state._reset_for_tests()
    seed()


if __name__ == "__main__":
    reset_and_seed()
