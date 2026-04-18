import threading
import unittest
from datetime import datetime

import numpy as np

from schema import AISuggestion, Casualty, Intervention, RespiratoryStatus, TriageCategory
from shared.state import PendingSuggestion, app_state


def _make_casualty(index: int = 1) -> Casualty:
    return Casualty(
        casualty_id=f"A{index}",
        triage_category=TriageCategory.UNASSESSED,
        respiratory_status=RespiratoryStatus.UNKNOWN,
        wounds=[],
        interventions=[],
    )


class SharedStateTests(unittest.TestCase):
    def setUp(self) -> None:
        app_state._reset_for_tests()

    def tearDown(self) -> None:
        app_state._reset_for_tests()

    def test_upsert_casualty_returns_copy(self) -> None:
        casualty = _make_casualty()

        app_state.upsert_casualty(casualty)

        stored = app_state.get_casualty("A1")
        self.assertIsNotNone(stored)
        self.assertEqual(stored, casualty)
        self.assertIsNot(stored, casualty)

    def test_add_and_confirm_ai_suggestion(self) -> None:
        suggestion = AISuggestion(
            timestamp=datetime.now(),
            source="vision",
            suggestion="A1: bleeding torso laceration",
            confidence=0.91,
        )

        suggestion_id = app_state.add_suggestion(suggestion)
        pending = app_state.get_pending_suggestions()

        self.assertEqual(len(pending), 1)
        self.assertIsInstance(pending[0], PendingSuggestion)
        self.assertEqual(pending[0].id, suggestion_id)
        self.assertEqual(pending[0].casualty_id, "A1")

        confirmed = app_state.confirm_suggestion(suggestion_id)

        self.assertIsNotNone(confirmed)
        self.assertEqual(confirmed.status, "confirmed")
        self.assertEqual(confirmed.raw.accepted_by_medic, True)
        self.assertEqual(app_state.get_pending_suggestions(), [])

    def test_add_intervention_updates_existing_casualty(self) -> None:
        casualty = _make_casualty()
        app_state.upsert_casualty(casualty)

        intervention = Intervention(type="tourniquet", location="left_leg")
        app_state.add_intervention("A1", intervention)

        stored = app_state.get_casualty("A1")
        self.assertIsNotNone(stored)
        self.assertEqual(len(stored.interventions), 1)
        self.assertEqual(stored.interventions[0].type, "tourniquet")

    def test_get_latest_frame_returns_copy(self) -> None:
        frame = np.arange(9, dtype=np.uint8).reshape(3, 3)
        app_state.set_latest_frame(frame)

        returned = app_state.get_latest_frame()
        self.assertIsNotNone(returned)
        returned[0, 0] = 255

        fresh = app_state.get_latest_frame()
        self.assertIsNotNone(fresh)
        self.assertEqual(int(fresh[0, 0]), 0)

    def test_concurrent_upserts_do_not_corrupt_roster(self) -> None:
        barrier = threading.Barrier(8)

        def writer(offset: int) -> None:
            barrier.wait()
            for index in range(10):
                casualty = _make_casualty(offset * 10 + index)
                app_state.upsert_casualty(casualty)

        threads = [threading.Thread(target=writer, args=(offset,)) for offset in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        roster = app_state.get_roster()
        self.assertEqual(len(roster), 80)
        self.assertEqual(len({casualty.casualty_id for casualty in roster}), 80)


if __name__ == "__main__":
    unittest.main()
