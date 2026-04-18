import json
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from vision.demo_profiles import get_demo_profile
from vision.video_processing import VideoProcessor
from vision.wound_detection import WoundAnalyzer


@dataclass
class FakeCasualty:
    id: str
    track_id: int
    bbox: tuple[int, int, int, int]
    triage_category: str
    triage_confidence: float
    wounds: list[object]
    interventions: list[object]
    respiratory_status: str
    respiratory_confidence: float
    last_seen_ts: float
    notes: list[str]


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


class FakeState:
    def __init__(self) -> None:
        self.casualties: dict[str, FakeCasualty] = {}
        self.suggestions: list[FakeSuggestion] = []
        self.latest_frame = None

    def upsert_casualty(self, casualty: FakeCasualty) -> None:
        self.casualties[casualty.id] = casualty

    def add_suggestion(self, suggestion: FakeSuggestion) -> None:
        self.suggestions.append(suggestion)

    def set_latest_frame(self, frame) -> None:
        self.latest_frame = frame

    def get_casualty(self, casualty_id: str):
        return self.casualties.get(casualty_id)


class FakeAnalyzer:
    def __init__(self) -> None:
        self.calls = 0

    def detect_person_rois(self, image):
        return [(10 + self.calls * 5, 20, 60, 80)]

    def analyze_image(self, image, pixels_per_cm=None):
        x = 22 + self.calls * 5
        self.calls += 1
        return {
            "wounds_detected": True,
            "wound_count": 1,
            "wounds": [
                {
                    "location": {"x": x, "y": 42, "width": 18, "height": 22},
                    "severity": 0.72,
                    "type": "laceration",
                    "location_type": "torso",
                    "bleeding": True,
                    "bleeding_detected": True,
                    "size_cm2": 8.5,
                    "confidence": 0.84,
                    "mask_area_px": 420,
                    "notes": "demo wound",
                }
            ],
            "overall_severity": 0.72,
            "priority_suggestion": "RED",
            "confidence": 0.84,
            "image_quality": 0.9,
        }

    def detection_mode(self):
        return "heuristic"


class MultiCasualtyFakeAnalyzer:
    def detect_person_rois(self, image):
        return [(10, 20, 70, 90), (120, 30, 70, 90)]

    def analyze_image(self, image, pixels_per_cm=None):
        return {
            "wounds_detected": True,
            "wound_count": 2,
            "wounds": [
                {
                    "location": {"x": 28, "y": 48, "width": 24, "height": 28},
                    "severity": 0.86,
                    "type": "laceration",
                    "location_type": "torso",
                    "bleeding": True,
                    "bleeding_detected": True,
                    "size_cm2": 16.2,
                    "confidence": 0.93,
                    "mask_area_px": 670,
                    "notes": "critical wound",
                },
                {
                    "location": {"x": 142, "y": 56, "width": 18, "height": 20},
                    "severity": 0.31,
                    "type": "burn",
                    "location_type": "limb",
                    "bleeding": False,
                    "bleeding_detected": False,
                    "size_cm2": 6.2,
                    "confidence": 0.81,
                    "mask_area_px": 310,
                    "notes": "secondary wound",
                },
            ],
            "overall_severity": 1.0,
            "priority_suggestion": "RED",
            "confidence": 0.9,
            "image_quality": 0.88,
        }

    def detection_mode(self):
        return "heuristic"


class BlinkingFakeAnalyzer:
    def __init__(self) -> None:
        self.calls = 0

    def detect_person_rois(self, image):
        return [(0, 0, image.shape[1], image.shape[0])]

    def analyze_image(self, image, pixels_per_cm=None):
        responses = [
            [
                {
                    "location": {"x": 32, "y": 40, "width": 24, "height": 24},
                    "severity": 0.7,
                    "type": "laceration",
                    "location_type": "torso",
                    "bleeding": True,
                    "bleeding_detected": True,
                    "size_cm2": 12.0,
                    "confidence": 0.88,
                    "mask_area_px": 480,
                    "notes": "stable wound",
                }
            ],
            [
                {
                    "location": {"x": 34, "y": 42, "width": 24, "height": 24},
                    "severity": 0.72,
                    "type": "laceration",
                    "location_type": "torso",
                    "bleeding": True,
                    "bleeding_detected": True,
                    "size_cm2": 12.4,
                    "confidence": 0.9,
                    "mask_area_px": 492,
                    "notes": "stable wound",
                },
                {
                    "location": {"x": 120, "y": 20, "width": 20, "height": 18},
                    "severity": 0.44,
                    "type": "abrasion",
                    "location_type": "limb",
                    "bleeding": True,
                    "bleeding_detected": True,
                    "size_cm2": 4.2,
                    "confidence": 0.86,
                    "mask_area_px": 210,
                    "notes": "transient false positive",
                },
            ],
        ]
        wounds = responses[min(self.calls, len(responses) - 1)]
        self.calls += 1
        return {
            "wounds_detected": True,
            "wound_count": len(wounds),
            "wounds": wounds,
            "overall_severity": 0.8,
            "priority_suggestion": "RED",
            "confidence": 0.9,
            "image_quality": 0.92,
        }

    def detection_mode(self):
        return "heuristic"


class VideoProcessingTests(unittest.TestCase):
    def test_recv_updates_state_and_keeps_track_stable(self) -> None:
        fake_state = FakeState()
        processor = VideoProcessor(
            FakeAnalyzer(),
            app_state=fake_state,
            casualty_factory=FakeCasualty,
            suggestion_factory=FakeSuggestion,
        )
        frame = np.full((120, 120, 3), 140, dtype=np.uint8)

        first = processor.recv(frame)
        second = processor.recv(frame)

        self.assertEqual(first.shape, frame.shape)
        self.assertEqual(second.shape, frame.shape)
        self.assertEqual(len(fake_state.casualties), 1)
        casualty = fake_state.casualties["A1"]
        self.assertEqual(casualty.id, "A1")
        self.assertEqual(casualty.track_id, 1)
        self.assertEqual(casualty.triage_category, "UNASSIGNED")
        self.assertEqual(len(fake_state.suggestions), 1)
        self.assertIsNotNone(fake_state.latest_frame)
        self.assertEqual(processor.last_result["casualties"][0]["alias"], "A1")
        self.assertEqual(processor.last_result["scene_summary"]["top_casualty_alias"], "A1")

    def test_video_processor_writes_annotated_video_and_frame_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            video_path = tmp_path / "input.avi"
            self._write_test_video(video_path)

            processor = VideoProcessor(WoundAnalyzer())
            result = processor.process_video(
                video_path,
                output_dir=tmp_path / "outputs",
                pixels_per_cm=10.0,
                frame_stride=1,
            )

            self.assertEqual(result["source_video"], str(video_path))
            self.assertGreaterEqual(result["processed_frames"], 1)
            self.assertGreaterEqual(len(result["frames"]), 1)
            self.assertTrue(result["summary"]["frames_with_wounds"] >= 1)
            self.assertIsNotNone(result["annotated_video"])
            self.assertTrue(Path(result["annotated_video"]).exists())

    def test_video_script_writes_json_payload(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            video_path = tmp_path / "input.avi"
            self._write_test_video(video_path)
            output_dir = tmp_path / "outputs"

            completed = __import__("subprocess").run(
                [
                    "python3",
                    "scripts/run_wound_detection_video.py",
                    str(video_path),
                    "--pixels-per-cm",
                    "10",
                    "--frame-stride",
                    "1",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            )

            json_path = output_dir / "input_video_wounds.json"
            self.assertIn("json:", completed.stdout)
            self.assertTrue(json_path.exists())

            payload = json.loads(json_path.read_text())
            self.assertGreaterEqual(payload["processed_frames"], 1)
            self.assertIn("summary", payload)
            self.assertIn("scene_summary", payload)

    def test_scene_summary_prioritizes_highest_risk_casualty(self) -> None:
        processor = VideoProcessor(MultiCasualtyFakeAnalyzer())
        frame = np.full((160, 240, 3), 150, dtype=np.uint8)

        annotated = processor.recv(frame)

        self.assertEqual(annotated.shape, frame.shape)
        self.assertIsNotNone(processor.last_result)
        scene_summary = processor.last_result["scene_summary"]
        self.assertEqual(scene_summary["tracked_casualties"], 2)
        self.assertEqual(scene_summary["top_casualty_alias"], "A1")
        self.assertEqual(scene_summary["top_casualty_priority"], "RED")
        self.assertGreater(scene_summary["top_casualty_score"], 0.7)
        self.assertIn("active bleeding", scene_summary["top_casualty_rationale"])

    def test_cached_render_reuses_last_detection_state(self) -> None:
        processor = VideoProcessor(FakeAnalyzer())
        frame = np.full((160, 240, 3), 150, dtype=np.uint8)

        processor.recv(frame)
        cached = processor._render_cached_frame(frame, frame_index=1)
        idle = processor._decorate_idle_frame(frame, frame_index=1)

        self.assertEqual(cached.shape, frame.shape)
        self.assertFalse(np.array_equal(cached, idle))

    def test_recv_with_analysis_roi_returns_cropped_frame(self) -> None:
        processor = VideoProcessor(FakeAnalyzer(), analysis_roi=(20, 30, 80, 60))
        frame = np.full((160, 240, 3), 150, dtype=np.uint8)

        annotated = processor.recv(frame)

        self.assertEqual(annotated.shape, (60, 80, 3))

    def test_demo_profile_lookup_returns_expected_profile(self) -> None:
        profile = get_demo_profile("DOD_111088902_12_18_hero.mp4")

        self.assertIsNotNone(profile)
        self.assertEqual(profile.name, "hero_casualty_closeup")
        self.assertEqual(profile.roi, (300, 50, 1200, 980))
        self.assertEqual(profile.clip_window_seconds, (2.9, 5.9))

    def test_temporal_stabilization_filters_transient_extra_wound(self) -> None:
        processor = VideoProcessor(BlinkingFakeAnalyzer())
        frame = np.full((160, 240, 3), 150, dtype=np.uint8)

        processor.recv(frame)
        processor.recv(frame)

        self.assertIsNotNone(processor.last_result)
        analysis = processor.last_result["analysis"]
        self.assertEqual(analysis["wound_count"], 1)
        self.assertEqual(len(analysis["wounds"]), 1)

    def test_process_video_clip_window_shortens_output_duration(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            video_path = tmp_path / "input.avi"
            self._write_test_video(video_path)

            processor = VideoProcessor(WoundAnalyzer())
            result = processor.process_video(
                video_path,
                output_dir=tmp_path / "outputs",
                pixels_per_cm=10.0,
                frame_stride=1,
                start_seconds=0.0,
                end_seconds=0.5,
            )

            self.assertLess(result["frame_count"], 6)
            self.assertLess(result["duration_ms"], 1000)

    def test_process_video_clip_window_restarts_stride_from_window_start(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            video_path = tmp_path / "input.avi"
            self._write_test_video(video_path)

            processor = VideoProcessor(WoundAnalyzer())
            result = processor.process_video(
                video_path,
                output_dir=tmp_path / "outputs",
                pixels_per_cm=10.0,
                frame_stride=2,
                start_seconds=0.2,
                end_seconds=0.7,
            )

            self.assertGreaterEqual(len(result["frames"]), 1)
            self.assertEqual(result["frames"][0]["frame_index"], 0)

    def _write_test_video(self, path: Path) -> None:
        writer = cv2.VideoWriter(
            str(path),
            cv2.VideoWriter_fourcc(*"MJPG"),
            6.0,
            (320, 240),
        )
        self.assertTrue(writer.isOpened())

        for offset in range(6):
            frame = np.full((240, 320, 3), 180, dtype=np.uint8)
            cv2.rectangle(
                frame,
                (80 + offset * 5, 90),
                (180 + offset * 5, 150),
                (0, 0, 255),
                thickness=-1,
            )
            writer.write(frame)

        writer.release()


if __name__ == "__main__":
    unittest.main()
