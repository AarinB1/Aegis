from __future__ import annotations

from pathlib import Path
from typing import Optional


DEFAULT_YOLO_ALIAS = "yolov8n.pt"


def resolve_yolo_weights(
    candidate: str | Path | None,
    *,
    allow_builtin_alias: bool = False,
) -> Optional[str]:
    if candidate is None:
        return None
    path = Path(candidate)
    if path.exists():
        return str(path)
    if allow_builtin_alias and path.name == DEFAULT_YOLO_ALIAS:
        # Ultralytics can resolve the canonical model alias from its cache or
        # download it on demand when the environment permits.
        return DEFAULT_YOLO_ALIAS
    return None


def resolve_sam_checkpoint(candidate: str | Path | None) -> Optional[str]:
    if candidate is None:
        return None
    path = Path(candidate)
    if path.exists():
        return str(path)
    return None


def format_runtime_report(summary: dict[str, str], warnings: list[str]) -> list[str]:
    lines = [
        f"detection-mode: {summary['detection_mode']}",
        f"person-detection: {summary['person_detection']}",
        f"wound-refinement: {summary['wound_refinement']}",
    ]
    lines.extend(f"warning: {warning}" for warning in warnings)
    return lines
