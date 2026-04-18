from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def main() -> None:
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)

    image = np.full((720, 960, 3), (170, 185, 205), dtype=np.uint8)

    cv2.circle(image, (480, 180), 80, (150, 170, 195), thickness=-1)
    cv2.rectangle(image, (360, 250), (600, 560), (155, 175, 200), thickness=-1)
    cv2.rectangle(image, (290, 280), (360, 520), (150, 170, 195), thickness=-1)
    cv2.rectangle(image, (600, 280), (670, 520), (150, 170, 195), thickness=-1)
    cv2.rectangle(image, (395, 560), (470, 700), (150, 170, 195), thickness=-1)
    cv2.rectangle(image, (490, 560), (565, 700), (150, 170, 195), thickness=-1)

    cv2.ellipse(image, (460, 390), (48, 18), 12, 0, 360, (20, 20, 210), thickness=-1)
    cv2.ellipse(image, (345, 410), (24, 55), -18, 0, 360, (30, 40, 185), thickness=-1)
    cv2.ellipse(image, (612, 350), (20, 42), 8, 0, 360, (65, 85, 170), thickness=-1)

    image_path = assets_dir / "test_wound.jpg"
    cv2.imwrite(str(image_path), image)

    video_path = assets_dir / "test_wound_video.avi"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        8.0,
        (image.shape[1], image.shape[0]),
    )
    if writer.isOpened():
        for offset in range(18):
            frame = image.copy()
            cv2.ellipse(
                frame,
                (460 + offset * 2, 390),
                (48, 18),
                12,
                0,
                360,
                (20, 20, 210),
                thickness=-1,
            )
            cv2.ellipse(
                frame,
                (345, 410 - offset),
                (24, 55),
                -18,
                0,
                360,
                (30, 40, 185),
                thickness=-1,
            )
            writer.write(frame)
        writer.release()


if __name__ == "__main__":
    main()
