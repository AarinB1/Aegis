import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class RunWoundDetectionScriptTests(unittest.TestCase):
    def test_script_writes_json_and_image_outputs(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            completed = subprocess.run(
                [
                    "python3",
                    "scripts/run_wound_detection.py",
                    "assets/test_wound.jpg",
                    "--pixels-per-cm",
                    "12",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            )

            json_path = output_dir / "test_wound_wounds.json"
            image_path = output_dir / "test_wound_annotated.jpg"

            self.assertIn("json:", completed.stdout)
            self.assertTrue(json_path.exists())
            self.assertTrue(image_path.exists())

            payload = json.loads(json_path.read_text())
            self.assertTrue(payload["wounds_detected"])
            self.assertGreaterEqual(payload["wound_count"], 1)


if __name__ == "__main__":
    unittest.main()
