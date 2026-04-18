import unittest
from dataclasses import dataclass

from vision.integration import DetectedWound, build_wound_suggestions, top_wound_suggestion


@dataclass
class FakeSuggestion:
    id: str
    casualty_id: str
    source: str
    field: str
    proposed_value: object
    confidence: float
    ts: float
    rationale: str


class IntegrationTests(unittest.TestCase):
    def test_build_wound_suggestions_returns_python_objects(self) -> None:
        analysis = {
            "wounds_detected": True,
            "wound_count": 2,
            "wounds": [
                {
                    "location": {"x": 10, "y": 20, "width": 30, "height": 40},
                    "severity": 0.55,
                    "type": "abrasion",
                    "location_type": "limb",
                    "bleeding": True,
                    "size_cm2": 8.2,
                    "confidence": 0.81,
                    "mask_area_px": 920,
                    "notes": "active bleeding signature",
                },
                {
                    "location": {"x": 60, "y": 80, "width": 25, "height": 35},
                    "severity": 0.33,
                    "type": "bruise",
                    "location_type": "limb",
                    "bleeding": False,
                    "size_cm2": 4.6,
                    "confidence": 0.7,
                    "mask_area_px": 500,
                    "notes": "soft tissue discoloration",
                },
            ],
        }

        suggestions = build_wound_suggestions(
            "A1",
            analysis,
            FakeSuggestion,
            now_ts=123.45,
        )

        self.assertEqual(len(suggestions), 2)
        self.assertEqual(suggestions[0].casualty_id, "A1")
        self.assertEqual(suggestions[0].source, "vision")
        self.assertEqual(suggestions[0].field, "wound")
        self.assertEqual(suggestions[0].ts, 123.45)
        self.assertIsInstance(suggestions[0].proposed_value, DetectedWound)
        self.assertEqual(suggestions[0].proposed_value.bbox, (10, 20, 40, 60))
        self.assertTrue(suggestions[0].proposed_value.bleeding_detected)
        self.assertEqual(suggestions[0].proposed_value.location, "limb")

    def test_top_wound_suggestion_prefers_bleeding_more_severe_wound(self) -> None:
        analysis = {
            "wounds_detected": True,
            "wound_count": 2,
            "wounds": [
                {
                    "location": {"x": 10, "y": 20, "width": 30, "height": 40},
                    "severity": 0.55,
                    "type": "abrasion",
                    "location_type": "torso",
                    "bleeding": True,
                    "size_cm2": 8.2,
                    "confidence": 0.81,
                    "mask_area_px": 920,
                    "notes": "active bleeding signature",
                },
                {
                    "location": {"x": 60, "y": 80, "width": 25, "height": 35},
                    "severity": 0.9,
                    "type": "bruise",
                    "location_type": "limb",
                    "bleeding": False,
                    "size_cm2": 10.6,
                    "confidence": 0.9,
                    "mask_area_px": 1200,
                    "notes": "soft tissue discoloration",
                },
            ],
        }

        suggestion = top_wound_suggestion("A1", analysis, FakeSuggestion, now_ts=77.0)

        self.assertIsNotNone(suggestion)
        self.assertEqual(suggestion.ts, 77.0)
        self.assertTrue(suggestion.proposed_value.bleeding)
        self.assertEqual(suggestion.proposed_value.location, "torso")


if __name__ == "__main__":
    unittest.main()
