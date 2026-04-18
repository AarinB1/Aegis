from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from schema import Casualty, Intervention, Suggestion, TriageCategory, Wound
from shared.state import app_state


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _build_demo_frame() -> np.ndarray:
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame[:, :, 1] = np.linspace(18, 42, frame.shape[1], dtype=np.uint8)
    frame[:, :, 2] = np.linspace(10, 28, frame.shape[0], dtype=np.uint8)[:, None]
    frame[80:640, 120:1160, :] += 12

    frame[120:260, 180:360, 2] = 200
    frame[120:260, 180:360, 1] = 40

    frame[260:430, 520:750, 2] = 170
    frame[260:430, 520:750, 1] = 150

    frame[390:560, 860:1080, 0] = 50
    frame[390:560, 860:1080, 1] = 70
    frame[390:560, 860:1080, 2] = 70

    frame[356:364, 300:980, :] = 120
    frame[160:560, 636:644, :] = 120
    return frame


def clear_demo_state() -> None:
    with app_state._lock:
        app_state._casualties.clear()
        app_state._suggestions.clear()
        app_state._interventions.clear()
        app_state._active_medevac = None
        app_state._latest_frame = None
        app_state._voice_state = ("idle", "")
        app_state._audit_log.clear()
        app_state._ai_enabled = True


def seed() -> None:
    now = _now()

    app_state.upsert_casualty(
        Casualty(
            id="A1",
            track_id=101,
            bbox=(180, 120, 360, 260),
            last_seen=now,
            wounds=[
                Wound(
                    bbox=(210, 150, 290, 225),
                    wound_type="junctional bleed",
                    body_region="limb",
                    bleeding=True,
                    size_cm2=19.5,
                    confidence=0.92,
                    severity=0.88,
                )
            ],
            triage=TriageCategory.RED,
            overall_severity=0.91,
            notes=["Tourniquet applied", "Responsive to command"],
            created_at=now - timedelta(minutes=6),
        )
    )

    app_state.upsert_casualty(
        Casualty(
            id="A2",
            track_id=102,
            bbox=(520, 260, 750, 430),
            last_seen=now - timedelta(seconds=12),
            wounds=[
                Wound(
                    bbox=(565, 292, 640, 360),
                    wound_type="torso laceration",
                    body_region="torso",
                    bleeding=True,
                    size_cm2=12.0,
                    confidence=0.74,
                    severity=0.54,
                )
            ],
            triage=TriageCategory.YELLOW,
            overall_severity=0.63,
            notes=["Breathing steady"],
            created_at=now - timedelta(minutes=5),
        )
    )

    app_state.upsert_casualty(
        Casualty(
            id="A3",
            track_id=103,
            bbox=(860, 390, 1080, 560),
            last_seen=now - timedelta(seconds=22),
            wounds=[],
            triage=TriageCategory.UNASSIGNED,
            overall_severity=0.28,
            notes=["Awaiting manual sort"],
            created_at=now - timedelta(minutes=3),
        )
    )

    app_state.add_suggestion(
        Suggestion(
            source="vision",
            casualty_id="A2",
            kind="wound_detected",
            payload={"priority": TriageCategory.YELLOW, "region": "torso", "bleeding": True},
            confidence=0.74,
            created_at=now - timedelta(seconds=40),
        )
    )

    app_state.add_suggestion(
        Suggestion(
            source="audio",
            casualty_id="A3",
            kind="distress_breathing",
            payload={"respiratory_rate": 28, "priority": TriageCategory.RED},
            confidence=0.68,
            created_at=now - timedelta(seconds=18),
        )
    )

    app_state.add_intervention(
        "A1",
        Intervention(
            casualty_id="A1",
            kind="tourniquet",
            location="left thigh",
            notes="Applied during initial sweep",
            timestamp=now - timedelta(minutes=2),
            source="manual",
        ),
    )

    app_state.set_voice_state("listening", "red tag A1")
    app_state.set_latest_frame(_build_demo_frame())
    app_state.set_active_medevac(
        "A1",
        {
            "line_1": "38S MB 4421 9912",
            "line_2": "31.40 secure",
            "line_3": "2 urgent",
            "line_4": "None",
            "line_5": "1 litter, 1 ambulatory",
            "line_6": "Enemy nearby",
            "line_7": "Smoke",
            "line_8": "2 US military",
            "line_9": "Open field west of compound",
        },
    )

    app_state.audit("demo", "seed_fake_data", {"casualties": 3, "pending_suggestions": 2})
    app_state.audit("ui", "set_demo_mode", {"mode": "Fake"})


def reset_and_seed() -> None:
    clear_demo_state()
    seed()


if __name__ == "__main__":
    reset_and_seed()
