import unittest

import cv2
import numpy as np
from fastapi.testclient import TestClient

from vision.api import app


class MobileApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_mobile_endpoint_returns_summary_and_analysis(self) -> None:
        image = np.full((320, 320, 3), 180, dtype=np.uint8)
        cv2.rectangle(image, (90, 110), (220, 180), (0, 0, 255), thickness=-1)
        encoded, buffer = cv2.imencode(".jpg", image)
        self.assertTrue(encoded)

        response = self.client.post(
            "/v1/mobile/analyze",
            files={"file": ("capture.jpg", buffer.tobytes(), "image/jpeg")},
            data={
                "casualty_id": "cas-7",
                "source_id": "rn-camera",
                "pixels_per_cm": "10",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["casualty_id"], "cas-7")
        self.assertEqual(payload["source_id"], "rn-camera")
        self.assertTrue(payload["analysis"]["wounds_detected"])
        self.assertGreaterEqual(payload["analysis"]["wound_count"], 1)
        self.assertTrue(payload["summary"]["bleeding_present"])
        self.assertGreater(payload["summary"]["total_visible_wound_area_cm2"], 0.0)
        self.assertIn(payload["summary"]["detection_mode"], {"heuristic", "yolo+heuristic", "heuristic+sam", "yolo+sam"})

    def test_health_endpoint_reports_detection_mode(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("detection_mode", payload)


if __name__ == "__main__":
    unittest.main()
