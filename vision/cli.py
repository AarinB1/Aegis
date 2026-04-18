from __future__ import annotations

import argparse
import json
from pathlib import Path

from vision.runtime import resolve_sam_checkpoint, resolve_yolo_weights
from vision.wound_detection import WoundAnalyzer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze an image for likely wounds.")
    parser.add_argument("image", type=Path, help="Path to the source image")
    parser.add_argument("--pixels-per-cm", type=float, default=None, help="Known image scale")
    parser.add_argument("--yolo-weights", type=str, default=None, help="Path to YOLO weights")
    parser.add_argument("--sam-checkpoint", type=str, default=None, help="Path to SAM checkpoint")
    parser.add_argument(
        "--allow-builtin-yolo",
        action="store_true",
        help="Allow the canonical yolov8n.pt alias to resolve through Ultralytics if local weights are missing",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    analyzer = WoundAnalyzer(
        yolo_weights=resolve_yolo_weights(args.yolo_weights, allow_builtin_alias=args.allow_builtin_yolo),
        sam_checkpoint=resolve_sam_checkpoint(args.sam_checkpoint),
    )
    result = analyzer.analyze_path(args.image, pixels_per_cm=args.pixels_per_cm)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
