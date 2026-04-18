import unittest

import cv2
import numpy as np

from vision.triage import infer_location_type
from vision.triage import calculate_wound_severity
from vision.wound_detection import CandidateRegion, WoundAnalyzer


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
        self.assertIn(result["wounds"][0]["location_type"], {"torso", "limb"})
        self.assertEqual(result["priority_suggestion"], "RED")
        self.assertGreaterEqual(result["overall_severity"], 0.7)

    def test_full_frame_fallback_uses_configured_scale(self) -> None:
        analyzer = WoundAnalyzer(fallback_pixels_per_cm=12.0)
        scale = analyzer._estimate_pixels_per_cm(
            np.zeros((640, 640, 3), dtype=np.uint8),
            [(0, 0, 640, 640)],
            person_detected=False,
        )

        self.assertEqual(scale, 12.0)

    def test_close_up_without_person_detection_defaults_location_to_limb(self) -> None:
        location = infer_location_type((100, 50, 80, 40), (0, 0, 640, 640), person_detected=False)
        self.assertEqual(location, "limb")

    def test_burn_like_candidate_is_not_marked_as_bleeding(self) -> None:
        analyzer = WoundAnalyzer()
        candidate = CandidateRegion(
            bbox=(50, 60, 160, 140),
            mask=np.zeros((320, 320), dtype=np.uint8),
            area_px=4200,
            mean_bgr=(75.0, 130.0, 180.0),
            mean_hsv=(18.0, 165.0, 180.0),
            redness_ratio=0.34,
            blood_ratio=0.08,
            orange_ratio=0.72,
            purple_ratio=0.02,
            person_roi=(0, 0, 320, 320),
            person_detected=False,
        )

        wound = analyzer._candidate_to_wound(candidate, pixels_per_cm=12.0)

        self.assertEqual(wound.type, "burn")
        self.assertFalse(wound.bleeding)
        self.assertEqual(wound.location_type, "limb")

    def test_rejects_elongated_sparse_strap_like_candidate(self) -> None:
        analyzer = WoundAnalyzer()
        candidate = CandidateRegion(
            bbox=(420, 600, 92, 233),
            mask=np.zeros((1080, 1920), dtype=np.uint8),
            area_px=4373,
            mean_bgr=(38.0, 64.0, 107.0),
            mean_hsv=(6.2, 138.9, 107.2),
            redness_ratio=1.0,
            blood_ratio=1.0,
            orange_ratio=0.822,
            purple_ratio=0.0,
            person_roi=(0, 0, 1920, 1080),
            person_detected=False,
        )

        self.assertFalse(analyzer._is_plausible_candidate(candidate, image_shape=(1080, 1920)))

    def test_keeps_long_cut_candidate_with_good_fill(self) -> None:
        analyzer = WoundAnalyzer()
        candidate = CandidateRegion(
            bbox=(229, 144, 202, 82),
            mask=np.zeros((640, 640), dtype=np.uint8),
            area_px=4757,
            mean_bgr=(44.0, 60.0, 152.0),
            mean_hsv=(4.0, 180.0, 150.0),
            redness_ratio=1.0,
            blood_ratio=0.999,
            orange_ratio=1.0,
            purple_ratio=0.0,
            person_roi=(0, 0, 640, 640),
            person_detected=False,
        )

        self.assertTrue(analyzer._is_plausible_candidate(candidate, image_shape=(640, 640)))

    def test_filters_person_rois_toward_casualty_like_boxes(self) -> None:
        analyzer = WoundAnalyzer()
        rois = [
            (20, 40, 90, 320),
            (160, 30, 92, 330),
            (260, 180, 300, 150),
            (610, 20, 85, 310),
        ]

        filtered = analyzer._filter_candidate_person_rois(rois, image_shape=(720, 1280))

        self.assertIn((260, 180, 300, 150), filtered)
        self.assertLess(len(filtered), len(rois))


if __name__ == "__main__":
    unittest.main()
