from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a side-by-side judge reel from source and annotated clips.")
    parser.add_argument("source_video", help="Path to the original source clip")
    parser.add_argument("annotated_video", help="Path to the annotated clip")
    parser.add_argument(
        "--output",
        required=True,
        help="Output video path, for example outputs/judge_reel.mp4",
    )
    parser.add_argument(
        "--title",
        default="AEGIS Vision Demo",
        help="Title banner shown above the side-by-side reel",
    )
    return parser.parse_args()


def _open_video(path: Path) -> cv2.VideoCapture:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise FileNotFoundError(f"unable to open video: {path}")
    return capture


def _resize_to_height(frame: np.ndarray, target_height: int) -> np.ndarray:
    height, width = frame.shape[:2]
    if height == target_height:
        return frame
    scale = target_height / max(height, 1)
    target_width = max(int(round(width * scale)), 1)
    return cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)


def _label_panel(frame: np.ndarray, label: str) -> np.ndarray:
    canvas = frame.copy()
    overlay = canvas.copy()
    cv2.rectangle(overlay, (12, 12), (260, 64), (12, 18, 32), thickness=-1)
    cv2.addWeighted(overlay, 0.72, canvas, 0.28, 0, canvas)
    cv2.putText(
        canvas,
        label,
        (24, 46),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.86,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return canvas


def build_reel(source_video: Path, annotated_video: Path, output_video: Path, title: str) -> Path:
    source_capture = _open_video(source_video)
    annotated_capture = _open_video(annotated_video)

    fps = source_capture.get(cv2.CAP_PROP_FPS)
    fps = float(fps) if fps and fps > 0 else 10.0

    ok_source, source_frame = source_capture.read()
    ok_annotated, annotated_frame = annotated_capture.read()
    if not ok_source or not ok_annotated:
        raise RuntimeError("unable to read first frame from one or both videos")

    target_height = max(source_frame.shape[0], annotated_frame.shape[0])
    source_frame = _resize_to_height(source_frame, target_height)
    annotated_frame = _resize_to_height(annotated_frame, target_height)
    gap = 20
    banner_height = 90
    combined_width = source_frame.shape[1] + annotated_frame.shape[1] + gap
    combined_height = target_height + banner_height

    output_video.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output_video),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (combined_width, combined_height),
    )
    if not writer.isOpened():
        raise RuntimeError(f"unable to create output video: {output_video}")

    try:
        while ok_source and ok_annotated:
            left = _label_panel(_resize_to_height(source_frame, target_height), "Source Clip")
            right = _label_panel(_resize_to_height(annotated_frame, target_height), "AEGIS Vision")

            canvas = np.zeros((combined_height, combined_width, 3), dtype=np.uint8)
            canvas[:banner_height, :] = (8, 12, 20)
            canvas[banner_height:, : left.shape[1]] = left
            canvas[banner_height:, left.shape[1] + gap :] = right

            cv2.putText(
                canvas,
                title,
                (24, 58),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.15,
                (255, 255, 255),
                3,
                cv2.LINE_AA,
            )
            cv2.putText(
                canvas,
                "Original scene on the left, casualty prioritization overlay on the right",
                (24, 82),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (160, 200, 235),
                2,
                cv2.LINE_AA,
            )

            writer.write(canvas)
            ok_source, source_frame = source_capture.read()
            ok_annotated, annotated_frame = annotated_capture.read()
    finally:
        source_capture.release()
        annotated_capture.release()
        writer.release()

    return output_video


def main() -> None:
    args = parse_args()
    output = build_reel(
        source_video=Path(args.source_video),
        annotated_video=Path(args.annotated_video),
        output_video=Path(args.output),
        title=args.title,
    )
    print(output)


if __name__ == "__main__":
    main()
