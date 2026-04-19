from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


DEFAULT_YOLO_ALIAS = "yolov8n.pt"
DEFAULT_SAM_FILENAME = "mobile_sam.pt"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODELS_DIR = REPO_ROOT / "models"
YOLO_WEIGHTS_ENV = "AEGIS_YOLO_WEIGHTS"
SAM_CHECKPOINT_ENV = "AEGIS_SAM_CHECKPOINT"
ALLOW_BUILTIN_YOLO_ENV = "AEGIS_ALLOW_BUILTIN_YOLO"


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


def allow_builtin_yolo_from_env() -> bool:
    value = os.getenv(ALLOW_BUILTIN_YOLO_ENV, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def default_yolo_candidate() -> Path:
    return DEFAULT_MODELS_DIR / DEFAULT_YOLO_ALIAS


def default_sam_candidate() -> Path:
    return DEFAULT_MODELS_DIR / DEFAULT_SAM_FILENAME


def resolve_runtime_yolo_weights(
    candidate: str | Path | None = None,
    *,
    allow_builtin_alias: bool | None = None,
) -> Optional[str]:
    requested = os.getenv(YOLO_WEIGHTS_ENV) or candidate or default_yolo_candidate()
    if allow_builtin_alias is None:
        allow_builtin_alias = allow_builtin_yolo_from_env()
    return resolve_yolo_weights(requested, allow_builtin_alias=allow_builtin_alias)


def resolve_runtime_sam_checkpoint(candidate: str | Path | None = None) -> Optional[str]:
    requested = os.getenv(SAM_CHECKPOINT_ENV) or candidate or default_sam_candidate()
    return resolve_sam_checkpoint(requested)


def format_runtime_report(summary: dict[str, str], warnings: list[str]) -> list[str]:
    lines = [
        f"detection-mode: {summary['detection_mode']}",
        f"person-detection: {summary['person_detection']}",
        f"wound-refinement: {summary['wound_refinement']}",
    ]
    lines.extend(f"warning: {warning}" for warning in warnings)
    return lines
