import unittest

import numpy as np

import schema
from vision.state_bridge import VisionStateBridge


class FakeSchemaState:
    def __init__(self) -> None:
        self.casualties: dict[str, object] = {}
        self.suggestions: list[object] = []
        self.latest_frame = None

    def upsert_casualty(self, casualty) -> None:
        casualty_id = getattr(casualty, "casualty_id", getattr(casualty, "id", "unknown"))
        self.casualties[casualty_id] = casualty

    def add_suggestion(self, suggestion) -> None:
        self.suggestions.append(suggestion)

    def set_latest_frame(self, frame) -> None:
        self.latest_frame = frame

    def get_casualty(self, casualty_id: str):
        return self.casualties.get(casualty_id)


class StateBridgeTests(unittest.TestCase):
    def test_publish_builds_current_schema_objects_and_dedupes_ai_logs(self) -> None:
        fake_state = FakeSchemaState()
        bridge = VisionStateBridge(
            app_state=fake_state,
            casualty_factory=schema.Casualty,
            suggestion_factory=schema.AISuggestion,
        )
        casualty_payload = {
            "alias": "A1",
            "track_id": 1,
            "bbox": (10, 20, 80, 140),
            "last_seen_ts": 1_716_000_000.0,
            "analysis": {
                "wounds_detected": True,
                "wound_count": 1,
                "wounds": [
                    {
                        "location": {"x": 24, "y": 40, "width": 20, "height": 22},
                        "severity": 0.82,
                        "type": "laceration",
                        "location_type": "torso",
                        "bleeding": True,
                        "bleeding_detected": True,
                        "size_cm2": 12.4,
                        "confidence": 0.88,
                        "mask_area_px": 440,
                        "notes": "demo wound",
                    }
                ],
                "overall_severity": 0.82,
                "priority_suggestion": "RED",
                "confidence": 0.88,
                "image_quality": 0.76,
            },
        }
        frame = np.zeros((32, 32, 3), dtype=np.uint8)

        bridge.publish(casualties=[casualty_payload], latest_frame=frame)
        bridge.publish(casualties=[casualty_payload], latest_frame=frame)

        stored = fake_state.casualties["A1"]
        self.assertIsInstance(stored, schema.Casualty)
        self.assertEqual(stored.casualty_id, "A1")
        self.assertEqual(stored.triage_category, schema.TriageCategory.UNASSESSED)
        self.assertEqual(len(stored.wounds), 1)
        self.assertIsInstance(stored.wounds[0], schema.Wound)
        self.assertEqual(stored.wounds[0].location, "torso")
        self.assertEqual(stored.wounds[0].severity, "severe")
        self.assertEqual(stored.wounds[0].area_cm2, 12.4)
        self.assertTrue(stored.wounds[0].active_bleeding)
        self.assertEqual(len(stored.ai_suggestions_log), 1)
        self.assertIsNotNone(fake_state.latest_frame)

        self.assertEqual(len(fake_state.suggestions), 1)
        self.assertIsInstance(fake_state.suggestions[0], schema.AISuggestion)
        self.assertEqual(fake_state.suggestions[0].source, "vision")
        self.assertIsNone(fake_state.suggestions[0].accepted_by_medic)
        self.assertIn("A1", fake_state.suggestions[0].suggestion)


if __name__ == "__main__":
    unittest.main()
