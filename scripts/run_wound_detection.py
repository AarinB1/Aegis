from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from vision.render import draw_wounds
from vision.runtime import format_runtime_report, resolve_sam_checkpoint, resolve_yolo_weights
from vision.wound_detection import WoundAnalyzer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the AEGIS wound-detection pipeline on one image and export artifacts."
    )
    parser.add_argument("image", type=Path, help="Input image path")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory for annotated image and JSON output",
    )
    parser.add_argument("--pixels-per-cm", type=float, default=None, help="Known image scale")
    parser.add_argument(
        "--yolo-weights",
        type=Path,
        default=Path("models/yolov8n.pt"),
        help="Path to YOLO weights",
    )
    parser.add_argument(
        "--sam-checkpoint",
        type=Path,
        default=Path("models/mobile_sam.pt"),
        help="Path to SAM checkpoint",
    )
    parser.add_argument(
        "--allow-builtin-yolo",
        action="store_true",
        help="Allow the canonical yolov8n.pt alias to resolve through Ultralytics if local weights are missing",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    analyzer = WoundAnalyzer(
        yolo_weights=resolve_yolo_weights(args.yolo_weights, allow_builtin_alias=args.allow_builtin_yolo),
        sam_checkpoint=resolve_sam_checkpoint(args.sam_checkpoint),
    )

    image = cv2.imread(str(args.image))
    if image is None:
        raise FileNotFoundError(f"unable to read image: {args.image}")

    result = analyzer.analyze_image(image, pixels_per_cm=args.pixels_per_cm)
    annotated = draw_wounds(image, result)

    stem = args.image.stem
    json_path = args.output_dir / f"{stem}_wounds.json"
    image_path = args.output_dir / f"{stem}_annotated.jpg"

    json_path.write_text(json.dumps(result, indent=2))
    cv2.imwrite(str(image_path), annotated)

    for line in format_runtime_report(analyzer.runtime_summary(), analyzer.runtime_warnings()):
        print(line)
    print(f"json: {json_path}")
    print(f"image: {image_path}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
