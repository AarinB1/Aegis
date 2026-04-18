import unittest

import cv2
import numpy as np

from vision.triage import calculate_wound_severity
from vision.wound_detection import WoundAnalyzer


class WoundDetectionTests(unittest.TestCase):
    def test_detects_red_region_as_bleeding_wound(self) -> None:
        image = np.full((320, 320, 3), 180, dtype=np.uint8)
        cv2.rectangle(image, (90, 110), (220, 180), (0, 0, 255), thickness=-1)

        analyzer = WoundAnalyzer()
        result = analyzer.analyze_image(image, pixels_per_cm=10.0)

        self.assertTrue(result["wounds_detected"])
        self.assertGreaterEqual(result["wound_count"], 1)
        first_wound = result["wounds"][0]
        self.assertTrue(first_wound["bleeding"])
        self.assertTrue(first_wound["bleeding_detected"])
        self.assertGreater(first_wound["size_cm2"], 0.0)
        self.assertGreater(first_wound["severity"], 0.3)
        self.assertIn(first_wound["location_type"], {"head", "torso", "limb"})
        self.assertIn(result["priority_suggestion"], {"RED", "YELLOW", "GREEN"})
        self.assertGreaterEqual(result["overall_severity"], first_wound["severity"])

    def test_larger_wound_scores_higher_than_smaller_wound(self) -> None:
        small_score = calculate_wound_severity(
            size_cm2=4.0,
            bleeding_detected=False,
            location_type="limb",
            wound_type="abrasion",
        )
        large_score = calculate_wound_severity(
            size_cm2=12.0,
            bleeding_detected=True,
            location_type="torso",
            wound_type="laceration",
        )

        self.assertLess(small_score, large_score)

    def test_torso_bleeding_wound_becomes_red_priority(self) -> None:
        image = np.full((400, 300, 3), 180, dtype=np.uint8)
        cv2.rectangle(image, (100, 140), (200, 240), (0, 0, 255), thickness=-1)

        analyzer = WoundAnalyzer()
        result = analyzer.analyze_image(image, pixels_per_cm=10.0)

        self.assertTrue(result["wounds_detected"])
        self.assertEqual(result["wounds"][0]["location_type"], "torso")
        self.assertEqual(result["priority_suggestion"], "RED")
        self.assertGreaterEqual(result["overall_severity"], 0.7)


if __name__ == "__main__":
    unittest.main()
