from __future__ import annotations

from typing import Any, Dict

import cv2
import numpy as np


def draw_wounds(image_bgr: np.ndarray, result: Dict[str, Any]) -> np.ndarray:
    canvas = image_bgr.copy()
    overlay = canvas.copy()

    for index, wound in enumerate(result["wounds"], start=1):
        box = wound["location"]
        x = int(box["x"])
        y = int(box["y"])
        w = int(box["width"])
        h = int(box["height"])

        severity = float(wound["severity"])
        color = (0, 220, 255) if severity < 0.45 else (0, 140, 255) if severity < 0.7 else (0, 0, 255)

        cv2.rectangle(overlay, (x, y), (x + w, y + h), color, thickness=-1)
        cv2.rectangle(canvas, (x, y), (x + w, y + h), color, thickness=2)

        label = f"#{index} {wound['type']} | sev {severity:.2f} | {wound['size_cm2']:.1f} cm2"
        cv2.putText(
            canvas,
            label,
            (x, max(20, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )

    cv2.addWeighted(overlay, 0.14, canvas, 0.86, 0, canvas)
    return canvas
