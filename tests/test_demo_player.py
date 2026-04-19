import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

from ui.components.demo_player import DemoPlayer


class DemoPlayerTests(unittest.TestCase):
    def test_scripted_mode_uses_canonical_hero_clip(self) -> None:
        controls_source = Path(
            "/Users/aaryansuri/Documents/New project/Aegis-ui/ui/components/controls.py"
        ).read_text()
        self.assertIn(
            '"Scripted MASCAL (90s)": {\n        "video_path": DEFAULT_HERO_VIDEO,',
            controls_source,
        )
        self.assertNotIn('"Live Vision": {', controls_source)

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
