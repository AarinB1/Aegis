import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

from ui.components.controls import DEMO_SCENARIOS
from ui.components.demo_catalog import (
    BACKUP_RECOGNITION_VIDEO,
    CURATED_CASUALTY_AUDIO,
    CURATED_DEMO_CLIPS,
    DEFAULT_HERO_VIDEO,
    MEDIC_POV_CLIP_MAP,
    OPTIONAL_THIRD_VIDEO,
    get_casualty_audio_cue,
)
from ui.components.demo_player import DemoPlayer


class DemoPlayerTests(unittest.TestCase):
    def test_demo_menu_exposes_two_curated_demo_clips(self) -> None:
        self.assertEqual(
            list(DEMO_SCENARIOS.keys()),
            ["Off", "Outdoor Face Wound Demo", "Indoor Treatment Demo"],
        )
        self.assertEqual(DEMO_SCENARIOS["Outdoor Face Wound Demo"]["video_path"], DEFAULT_HERO_VIDEO)
        self.assertEqual(DEMO_SCENARIOS["Outdoor Face Wound Demo"]["clip_key"], "primary")
        self.assertEqual(DEMO_SCENARIOS["Indoor Treatment Demo"]["video_path"], BACKUP_RECOGNITION_VIDEO)
        self.assertEqual(DEMO_SCENARIOS["Indoor Treatment Demo"]["clip_key"], "backup")

    def test_curated_catalog_matches_locked_clip_contract(self) -> None:
        self.assertGreaterEqual(len(CURATED_DEMO_CLIPS), 3)
        self.assertTrue(all(clip.video_path.exists() for clip in CURATED_DEMO_CLIPS.values()))
        self.assertEqual(CURATED_DEMO_CLIPS["primary"].video_path, DEFAULT_HERO_VIDEO)
        self.assertEqual(CURATED_DEMO_CLIPS["backup"].video_path, BACKUP_RECOGNITION_VIDEO)
        self.assertEqual(CURATED_DEMO_CLIPS["optional_third"].video_path, OPTIONAL_THIRD_VIDEO)
        self.assertEqual(
            CURATED_DEMO_CLIPS["primary"].expected_output,
            (
                "1 casualty",
                "1 primary face/neck bleeding wound",
                "no giant full-body track box",
                "no extra low-confidence roster entries",
            ),
        )

    def test_medic_pov_clip_map_uses_distinct_existing_videos(self) -> None:
        self.assertEqual(set(MEDIC_POV_CLIP_MAP), {"MEDIC_HAYES", "MEDIC_RIOS"})
        mapped_paths = {path.resolve() for path in MEDIC_POV_CLIP_MAP.values()}
        self.assertEqual(len(mapped_paths), 2)
        self.assertTrue(all(path.exists() for path in mapped_paths))
        self.assertEqual(MEDIC_POV_CLIP_MAP["MEDIC_HAYES"], BACKUP_RECOGNITION_VIDEO)
        self.assertEqual(MEDIC_POV_CLIP_MAP["MEDIC_RIOS"], OPTIONAL_THIRD_VIDEO)

    def test_curated_casualty_audio_cues_are_repo_backed(self) -> None:
        self.assertEqual(set(CURATED_CASUALTY_AUDIO), {"A1", "A2", "A3"})
        for casualty_id in CURATED_CASUALTY_AUDIO:
            cue = get_casualty_audio_cue(casualty_id)
            self.assertIsNotNone(cue)
            self.assertTrue(cue.audio_path.exists())
            self.assertIn(cue.audio_path.suffix.lower(), {".wav", ".mp3", ".m4a", ".ogg", ".flac"})

    def test_demo_player_uses_demo_profile_clip_window_and_crop(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            video_path = tmp_path / "DOD_111088902_12_18_hero.avi"
            script_path = tmp_path / "scenario.json"

            self._write_test_video(video_path, size=(1600, 1200))
            script_path.write_text(json.dumps({"events": []}))

            player = DemoPlayer(video_path=video_path, script_path=script_path)
            capture = cv2.VideoCapture(str(video_path))
            try:
                start_frame, end_frame = player._clip_bounds(capture, fps=30.0)
            finally:
                capture.release()

            self.assertEqual((start_frame, end_frame), (87, 177))

            frame = np.full((1200, 1600, 3), 180, dtype=np.uint8)
            cropped = player._prepare_frame(frame)
            self.assertEqual(cropped.shape, (980, 1200, 3))

    def test_demo_player_routes_frames_through_processor(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            video_path = tmp_path / "DOD_111088902_12_18_hero.avi"
            script_path = tmp_path / "scenario.json"

            self._write_test_video(video_path, size=(1600, 1200))
            script_path.write_text(json.dumps({"events": []}))

            player = DemoPlayer(video_path=video_path, script_path=script_path)
            seen_shapes: list[tuple[int, ...]] = []

            def fake_recv(frame):
                seen_shapes.append(frame.shape)
                player._stop_event.set()
                return frame

            player._processor = SimpleNamespace(recv=fake_recv, reset=lambda: None)
            player._resume_event.set()
            player._stop_event.clear()

            player._video_loop()

            self.assertEqual(len(seen_shapes), 1)
            self.assertEqual(seen_shapes[0], (1200, 1600, 3))

    def _write_test_video(self, path: Path, size: tuple[int, int]) -> None:
        width, height = size
        writer = cv2.VideoWriter(
            str(path),
            cv2.VideoWriter_fourcc(*"MJPG"),
            30.0,
            (width, height),
        )
        self.assertTrue(writer.isOpened())

        frame = np.full((height, width, 3), 140, dtype=np.uint8)
        for _ in range(240):
            writer.write(frame)

        writer.release()


if __name__ == "__main__":
    unittest.main()
