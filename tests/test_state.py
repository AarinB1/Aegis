from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from schema import Casualty, Suggestion, TriageCategory
from shared.state import app_state


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _reset_state() -> None:
    with app_state._lock:
        app_state._casualties.clear()
        app_state._suggestions.clear()
        app_state._interventions.clear()
        app_state._active_medevac = None
        app_state._latest_frame = None
        app_state._voice_state = ("idle", "")
        app_state._audit_log.clear()
        app_state._ai_enabled = True


def _make_casualty(index: int = 1) -> Casualty:
    return Casualty(
        id=f"casualty-{index}",
        track_id=index,
        bbox=(index, index + 1, index + 2, index + 3),
        last_seen=_now(),
        wounds=[],
        triage=TriageCategory.UNASSIGNED,
        overall_severity=0.5,
        notes=[],
        created_at=_now(),
    )


@pytest.fixture(autouse=True)
def clean_app_state():
    _reset_state()
    yield
    _reset_state()


def test_suggestion_with_black_priority_raises_value_error() -> None:
    with pytest.raises(ValueError):
        Suggestion(
            source="triage",
            casualty_id="casualty-1",
            kind="triage_proposal",
            payload={"priority": TriageCategory.BLACK},
            confidence=0.99,
        )


def test_upsert_casualty_returns_equal_but_distinct_copy() -> None:
    casualty = _make_casualty()

    app_state.upsert_casualty(casualty)

    stored = app_state.get_casualty(casualty.id)

    assert stored == casualty
    assert stored is not casualty


def test_concurrent_upserts_do_not_corrupt_state() -> None:
    thread_count = 10
    casualties_per_thread = 25
    barrier = threading.Barrier(thread_count)

    def writer(thread_index: int) -> None:
        barrier.wait()
        for offset in range(casualties_per_thread):
            casualty_index = thread_index * casualties_per_thread + offset
            app_state.upsert_casualty(_make_casualty(casualty_index))

    threads = [
        threading.Thread(target=writer, args=(thread_index,))
        for thread_index in range(thread_count)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    roster = app_state.get_roster()

    assert len(roster) == thread_count * casualties_per_thread
    assert len({casualty.id for casualty in roster}) == len(roster)


def test_confirm_suggestion_updates_status_and_audits() -> None:
    suggestion_id = app_state.add_suggestion(
        Suggestion(
            source="vision",
            casualty_id="casualty-7",
            kind="wound_detected",
            payload={"priority": TriageCategory.RED},
            confidence=0.87,
        )
    )

    confirmed = app_state.confirm_suggestion(suggestion_id)
    audit_log = app_state.get_audit_log()

    assert confirmed is not None
    assert confirmed.status == "confirmed"
    assert app_state.get_pending_suggestions() == []
    assert any(
        entry.action == "confirm_suggestion"
        and entry.details["suggestion_id"] == suggestion_id
        for entry in audit_log
    )


def test_get_latest_frame_returns_copy() -> None:
    frame = np.arange(9, dtype=np.uint8).reshape(3, 3)
    app_state.set_latest_frame(frame)

    returned = app_state.get_latest_frame()
    assert returned is not None

    returned[0, 0] = 255

    fresh = app_state.get_latest_frame()

    assert fresh is not None
    assert fresh[0, 0] == 0
