from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.build_judge_reel import build_reel
from vision.demo_profiles import get_demo_profile, parse_roi
from vision.runtime import format_runtime_report, resolve_sam_checkpoint, resolve_yolo_weights
from vision.video_processing import VideoProcessor
from vision.wound_detection import WoundAnalyzer


@dataclass(frozen=True)
class JudgeScenario:
    key: str
    source_candidates: tuple[str, ...]
    title: str
    use_demo_profile: bool = True


SCENARIOS: dict[str, JudgeScenario] = {
    "hero": JudgeScenario(
        key="hero",
        source_candidates=(
            "assets/demo_videos/DOD_111088902_12_18_hero.mp4",
            "outputs/dvids_review/recommended/DOD_111088902_12_18_hero.mp4",
        ),
        title="AEGIS Vision Demo - Hero Casualty",
    ),
    "indoor": JudgeScenario(
        key="indoor",
        source_candidates=(
            "assets/demo_videos/DOD_110359890_best_indoor_treatment_00-00_00-09.mp4",
            "outputs/dvids_review/new_segments/DOD_110359890_best_indoor_treatment_00-00_00-09.mp4",
        ),
        title="AEGIS Vision Demo - Indoor Treatment",
    ),
    "torso": JudgeScenario(
        key="torso",
        source_candidates=(
            "assets/demo_videos/DOD_100500026_best_indoor_torso_assessment_01-23_01-35.mp4",
            "outputs/dvids_review/new_segments/DOD_100500026_best_indoor_torso_assessment_01-23_01-35.mp4",
        ),
        title="AEGIS Vision Demo - Torso Assessment",
    ),
    "tracking-backup": JudgeScenario(
        key="tracking-backup",
        source_candidates=(
            "outputs/dvids_review/recommended/DOD_111088902_06_12_tracking_backup.mp4",
        ),
        title="AEGIS Vision Demo - Tracking Backup",
        use_demo_profile=False,
    ),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a canonical AEGIS judge demo clip with the best available vision runtime settings."
    )
    parser.add_argument("scenario", choices=sorted(SCENARIOS), help="Named demo scenario to run")
    parser.add_argument(
        "--source-video",
        type=Path,
        default=None,
        help="Optional explicit source clip override",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/judge_demo"),
        help="Directory for demo exports",
    )
    parser.add_argument("--pixels-per-cm", type=float, default=None, help="Known image scale")
    parser.add_argument("--frame-stride", type=int, default=None, help="Optional manual frame stride override")
    parser.add_argument("--max-frames", type=int, default=None, help="Optional cap on analyzed frames")
    parser.add_argument("--start-seconds", type=float, default=None, help="Optional manual subclip start")
    parser.add_argument("--end-seconds", type=float, default=None, help="Optional manual subclip end")
    parser.add_argument(
        "--roi",
        type=str,
        default=None,
        help="Optional manual crop as x,y,width,height",
    )
    parser.add_argument(
        "--yolo-weights",
        type=Path,
        default=Path("models/yolov8n.pt"),
        help="Path to YOLO weights, or the canonical yolov8n.pt alias",
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
        "--skip-reel",
        action="store_true",
        help="Only export the annotated clip and JSON timeline",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Print the full video-analysis JSON payload to stdout",
    )
    return parser


def _resolve_source_video(args: argparse.Namespace) -> Path:
    if args.source_video is not None:
        if not args.source_video.exists():
            raise FileNotFoundError(f"unable to read source video: {args.source_video}")
        return args.source_video

    scenario = SCENARIOS[args.scenario]
    for candidate in scenario.source_candidates:
        path = REPO_ROOT / candidate
        if path.exists():
            return path
    searched = ", ".join(scenario.source_candidates)
    raise FileNotFoundError(f"unable to find any source clip for scenario '{args.scenario}': {searched}")


def main() -> None:
    args = build_parser().parse_args()
    source_video = _resolve_source_video(args)
    scenario = SCENARIOS[args.scenario]
    demo_profile = get_demo_profile(source_video) if scenario.use_demo_profile else None
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

    output_dir = args.output_dir / args.scenario
    output_dir.mkdir(parents=True, exist_ok=True)

    analyzer = WoundAnalyzer(
        yolo_weights=resolve_yolo_weights(args.yolo_weights, allow_builtin_alias=args.allow_builtin_yolo),
        sam_checkpoint=resolve_sam_checkpoint(args.sam_checkpoint),
    )
    processor = VideoProcessor(analyzer, analysis_roi=analysis_roi)
    result = processor.process_video(
        source_video,
        output_dir=output_dir,
        pixels_per_cm=args.pixels_per_cm,
        frame_stride=frame_stride,
        max_frames=args.max_frames,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
    )

    json_path = output_dir / f"{source_video.stem}_video_wounds.json"
    json_path.write_text(json.dumps(result, indent=2))

    for line in format_runtime_report(analyzer.runtime_summary(), analyzer.runtime_warnings()):
        print(line)
    print(f"scenario: {scenario.key}")
    print(f"source-video: {source_video}")
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
        print(f"annotated-video: {result['annotated_video']}")
    print(
        "focus-casualty: "
        f"{result['scene_summary']['top_casualty_alias']} "
        f"{result['scene_summary']['top_casualty_priority']} | "
        f"{result['scene_summary']['top_casualty_rationale']}"
    )
    print(
        "summary: "
        f"tracked={result['summary']['peak_tracked_casualties']} "
        f"wounds={result['summary']['peak_wound_count']} "
        f"priority={result['summary']['priority_suggestion']}"
    )

    if not args.skip_reel and result["annotated_video"]:
        reel_path = output_dir / f"{source_video.stem}_judge_reel.mp4"
        build_reel(
            source_video=source_video,
            annotated_video=Path(result["annotated_video"]),
            output_video=reel_path,
            title=scenario.title,
        )
        print(f"judge-reel: {reel_path}")

    if args.print_json:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
