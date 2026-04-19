from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import logging
from pathlib import Path
import re

from schema import AISuggestion, Casualty, TriageCategory
from shared.state import app_state
from simulation.casualties import SimCasualty, evaluate_all, get_casualties

REPO_ROOT = Path(__file__).resolve().parents[2]
LOGGER = logging.getLogger(__name__)

simulation_assets: dict[str, dict[str, object]] = {}


def _priority_to_triage(priority: int) -> TriageCategory:
    if priority == 1:
        return TriageCategory.IMMEDIATE
    if priority == 2:
        return TriageCategory.DELAYED
    if priority == 3:
        return TriageCategory.MINIMAL
    return TriageCategory.UNASSESSED


def _next_available_id(occupied_ids: set[str]) -> str:
    numeric_ids = [
        int(match.group(1))
        for casualty_id in occupied_ids
        if (match := re.fullmatch(r"A(\d+)", casualty_id))
    ]
    next_index = max(numeric_ids, default=0) + 1
    candidate = f"A{next_index}"
    while candidate in occupied_ids:
        next_index += 1
        candidate = f"A{next_index}"
    return candidate


def resolve_sim_asset(relative_path: str) -> Path | None:
    """Resolves a simulation asset path like "../audio/normal.wav" to an
    absolute path rooted at repo root. Returns None if the file doesn't
    exist."""
    if not relative_path:
        return None

    raw_value = str(relative_path).strip()
    if not raw_value:
        return None

    asset_path = Path(raw_value)
    if asset_path.is_absolute():
        return asset_path if asset_path.exists() else None

    normalized = raw_value
    while normalized.startswith("../"):
        normalized = normalized[3:]
    normalized = normalized.lstrip("./")

    resolved = (REPO_ROOT / normalized).resolve()
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError:
        return None
    return resolved if resolved.exists() else None


def _effective_casualty_id(sim: SimCasualty, occupied_ids: set[str], include_existing: bool) -> str:
    casualty_id = str(sim.id)
    if casualty_id not in occupied_ids:
        return casualty_id

    if not include_existing:
        return casualty_id

    # Neal's current sample IDs overlap the baseline A1/A2 seeds; remap
    # only on collision so mixed mode can preserve all currently working
    # seeded casualties in a single roster.
    return _next_available_id(occupied_ids)


def _normalize_reasoning(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, (list, tuple, set)):
        parts = [str(part).strip() for part in value if str(part).strip()]
        return " ".join(parts) if parts else None
    text = str(value).strip()
    return text or None


def seed_simulation(include_existing: bool = True) -> None:
    """
    Seeds app_state with Neal's simulation casualties. If include_existing
    is True, leaves any currently-seeded casualties in place and adds
    Neal's on top.
    """
    if not include_existing:
        app_state._reset_for_tests()

    simulation_assets.clear()
    occupied_ids = {casualty.casualty_id for casualty in app_state.get_roster()}
    seeded_at = datetime.now(timezone.utc)
    evaluated_by_id: dict[str, dict[str, object]] = {}

    try:
        evaluated_by_id = {
            str(item.get("id", "") or ""): item
            for item in evaluate_all()
            if str(item.get("id", "") or "").strip()
        }
    except Exception as exc:
        LOGGER.warning("Simulation triage reasoning unavailable; continuing without rationale: %s", exc)

    for sim in get_casualties():
        source_id = str(getattr(sim, "id", "") or "")
        casualty_id = _effective_casualty_id(sim, occupied_ids, include_existing)
        occupied_ids.add(casualty_id)

        casualty = Casualty(
            casualty_id=casualty_id,
            triage_category=_priority_to_triage(int(getattr(sim, "priority", 0) or 0)),
            triage_confirmed_by_medic=False,
            posture="supine",
            responsive=None,
            wounds=[],
            medic_notes="",
        )
        app_state.upsert_casualty(casualty)

        suggestion = AISuggestion(
            timestamp=seeded_at,
            source="fusion",
            suggestion=f"{casualty_id}: {getattr(sim, 'output_script', '')}",
            confidence=0.85,
            accepted_by_medic=None,
        )
        app_state.add_suggestion(suggestion)

        simulation_assets[casualty_id] = {
            "audio": resolve_sim_asset(str(getattr(sim, "audio", "") or "")),
            "image": resolve_sim_asset(str(getattr(sim, "image", "") or "")),
            "diagnosis": str(getattr(sim, "output_script", "") or "").strip(),
            "reasoning": _normalize_reasoning(evaluated_by_id.get(source_id, {}).get("reasoning")),
            "location": getattr(sim, "location", None),
            "source_id": source_id or casualty_id,
        }


def get_simulation_assets() -> dict[str, dict]:
    """Returns {casualty_id: {audio, image, diagnosis, reasoning}} for all sim casualties."""
    return deepcopy(simulation_assets)


def clear_simulation_assets() -> None:
    simulation_assets.clear()
