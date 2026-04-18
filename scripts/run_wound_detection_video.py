from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from vision.video_processing import VideoProcessor
from vision.demo_profiles import get_demo_profile, parse_roi
from vision.runtime import format_runtime_report, resolve_sam_checkpoint, resolve_yolo_weights
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
        default=None,
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
    parser.add_argument(
        "--allow-builtin-yolo",
        action="store_true",
        help="Allow the canonical yolov8n.pt alias to resolve through Ultralytics if local weights are missing",
    )
    parser.add_argument(
        "--demo-profile",
        choices=("none", "auto"),
        default="none",
        help="Use a clip-specific demo optimization profile when one is available",
    )
    parser.add_argument(
        "--roi",
        type=str,
        default=None,
        help="Optional manual crop as x,y,width,height to focus the analysis on a casualty region",
    )
    parser.add_argument(
        "--start-seconds",
        type=float,
        default=None,
        help="Optional start time offset for processing a subclip",
    )
    parser.add_argument(
        "--end-seconds",
        type=float,
        default=None,
        help="Optional end time offset for processing a subclip",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    analyzer = WoundAnalyzer(
        yolo_weights=resolve_yolo_weights(args.yolo_weights, allow_builtin_alias=args.allow_builtin_yolo),
        sam_checkpoint=resolve_sam_checkpoint(args.sam_checkpoint),
    )
    demo_profile = get_demo_profile(args.video) if args.demo_profile == "auto" else None
    analysis_roi = parse_roi(args.roi) if args.roi else None
    if analysis_roi is None and demo_profile is not None:
        analysis_roi = demo_profile.roi
    frame_stride = args.frame_stride if args.frame_stride is not None else (
        demo_profile.recommended_frame_stride if demo_profile is not None else 3
    )
    start_seconds = args.start_seconds
    end_seconds = args.end_seconds
    if demo_profile is not None and demo_profile.clip_window_seconds is not None:
        if start_seconds is None:
            start_seconds = demo_profile.clip_window_seconds[0]
        if end_seconds is None:
            end_seconds = demo_profile.clip_window_seconds[1]

    processor = VideoProcessor(analyzer, analysis_roi=analysis_roi)
    result = processor.process_video(
        args.video,
        output_dir=args.output_dir,
        pixels_per_cm=args.pixels_per_cm,
        frame_stride=frame_stride,
        max_frames=args.max_frames,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
    )

    json_path = args.output_dir / f"{args.video.stem}_video_wounds.json"
    json_path.write_text(json.dumps(result, indent=2))

    for line in format_runtime_report(analyzer.runtime_summary(), analyzer.runtime_warnings()):
        print(line)
    if demo_profile is not None:
        print(f"demo-profile: {demo_profile.name}")
        if demo_profile.note:
            print(f"demo-note: {demo_profile.note}")
    if analysis_roi is not None:
        print(f"roi: {analysis_roi}")
    if start_seconds is not None or end_seconds is not None:
        print(f"clip-window: start={start_seconds or 0.0}s end={end_seconds if end_seconds is not None else 'full'}")
    print(f"json: {json_path}")
    if result["annotated_video"]:
        print(f"video: {result['annotated_video']}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
