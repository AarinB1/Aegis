from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from vision.video_processing import VideoProcessor
from vision.wound_detection import WoundAnalyzer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the AEGIS wound-detection pipeline on a video and export JSON plus an annotated video."
    )
    parser.add_argument("video", type=Path, help="Input video path")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory for JSON and annotated video output",
    )
    parser.add_argument("--pixels-per-cm", type=float, default=None, help="Known image scale")
    parser.add_argument(
        "--frame-stride",
        type=int,
        default=3,
        help="Analyze every Nth frame to keep runtime practical for demo footage",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Optional cap on analyzed frames",
    )
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
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    analyzer = WoundAnalyzer(
        yolo_weights=str(args.yolo_weights) if args.yolo_weights.exists() else None,
        sam_checkpoint=str(args.sam_checkpoint) if args.sam_checkpoint.exists() else None,
    )
    processor = VideoProcessor(analyzer)
    result = processor.process_video(
        args.video,
        output_dir=args.output_dir,
        pixels_per_cm=args.pixels_per_cm,
        frame_stride=args.frame_stride,
        max_frames=args.max_frames,
    )

    json_path = args.output_dir / f"{args.video.stem}_video_wounds.json"
    json_path.write_text(json.dumps(result, indent=2))

    print(f"json: {json_path}")
    if result["annotated_video"]:
        print(f"video: {result['annotated_video']}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
