import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np


class JudgeDemoScriptTests(unittest.TestCase):
    def test_script_runs_with_source_override_and_writes_outputs(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            video_path = tmp_path / "input.avi"
            output_dir = tmp_path / "outputs"
            self._write_test_video(video_path)

            completed = subprocess.run(
                [
                    "python3",
                    "scripts/run_judge_demo.py",
                    "hero",
                    "--source-video",
                    str(video_path),
                    "--output-dir",
                    str(output_dir),
                    "--skip-reel",
                ],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            )

            json_path = output_dir / "hero" / "input_video_wounds.json"
            self.assertIn("scenario: hero", completed.stdout)
            self.assertIn("detection-mode:", completed.stdout)
            self.assertTrue(json_path.exists())

            payload = json.loads(json_path.read_text())
            self.assertGreaterEqual(payload["processed_frames"], 1)
            self.assertIsNotNone(payload["annotated_video"])

    def _write_test_video(self, path: Path) -> None:
        writer = cv2.VideoWriter(
            str(path),
            cv2.VideoWriter_fourcc(*"MJPG"),
            6.0,
            (320, 240),
        )
        self.assertTrue(writer.isOpened())

        for offset in range(8):
            frame = np.full((240, 320, 3), 180, dtype=np.uint8)
            cv2.rectangle(
                frame,
                (80 + offset * 4, 90),
                (180 + offset * 4, 150),
                (0, 0, 255),
                thickness=-1,
            )
            writer.write(frame)

        writer.release()


if __name__ == "__main__":
    unittest.main()
