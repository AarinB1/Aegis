# scenario_ranker.py

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from schema import Casualty, RespiratoryStatus, TriageCategory, Wound
from shared.state import app_state
from triage_engine import TriageEngine


PRIORITY_RANK = {
    TriageCategory.IMMEDIATE: 0,
    TriageCategory.DELAYED: 1,
    TriageCategory.MINIMAL: 2,
    TriageCategory.UNASSESSED: 3,
    TriageCategory.EXPECTANT: 4,
    TriageCategory.DECEASED: 5,
}


def _severity_label(severity_float: float) -> str:
    if severity_float >= 0.7:
        return "severe"
    if severity_float >= 0.4:
        return "moderate"
    return "minor"


def _scene_tag_from_path(json_path: Path) -> str:
    parts = json_path.parts
    if "judge_demo" in parts:
        idx = parts.index("judge_demo")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return json_path.stem[:10]


def _wounds_for_casualty(casualty_info: dict, all_wounds: list[dict]) -> list[dict]:
    cx, cy, cw, ch = casualty_info.get("bbox", (0, 0, 0, 0))
    matched = []

    for wound in all_wounds:
        loc = wound.get("location", {})
        wx = loc.get("x", 0)
        wy = loc.get("y", 0)
        ww = loc.get("width", 0)
        wh = loc.get("height", 0)

        wound_cx = wx + ww / 2
        wound_cy = wy + wh / 2

        if cx <= wound_cx <= cx + cw and cy <= wound_cy <= cy + ch:
            matched.append(wound)

    if not matched and casualty_info.get("wound_count", 0) > 0:
        matched = all_wounds

    return matched


def _casualty_from_vision(casualty_info: dict, wounds_raw: list[dict], casualty_id: str) -> Casualty:
    wounds: list[Wound] = []

    for wound_raw in wounds_raw:
        sev = float(wound_raw.get("severity", 0.0))
        wounds.append(
            Wound(
                location=wound_raw.get("location_type", "unknown") or "unknown",
                area_cm2=float(wound_raw.get("size_cm2", 0.0)),
                severity=_severity_label(sev),
                active_bleeding=bool(wound_raw.get("bleeding", False)),
                ai_confidence=float(wound_raw.get("confidence", 0.0)),
            )
        )

    if not wounds and casualty_info.get("wound_count", 0) > 0:
        wounds.append(
            Wound(
                location="limb",
                area_cm2=5.0,
                severity=_severity_label(float(casualty_info.get("overall_severity", 0.5))),
                active_bleeding=bool(casualty_info.get("bleeding_wound_count", 0) > 0),
                ai_confidence=float(casualty_info.get("confidence", 0.5)),
            )
        )

    return Casualty(
        casualty_id=casualty_id,
        triage_category=TriageCategory.UNASSESSED,
        responsive=True,
        respiratory_status=RespiratoryStatus.UNKNOWN,
        respiratory_rate=None,
        wounds=wounds,
    )


def load_casualties_from_jsons(json_paths: list[Path]) -> list[tuple[Casualty, str]]:
    combined = []
    next_id = 1

    for json_path in json_paths:
        scene_tag = _scene_tag_from_path(json_path)

        try:
            vision_data = json.loads(json_path.read_text())
        except Exception as e:
            print(f"[skip] {json_path}: {e}")
            continue

        frames = vision_data.get("frames", [])
        if not frames:
            continue

        last_frame = frames[-1]
        top_casualties = last_frame.get("scene_summary", {}).get("top_casualties", [])
        all_wounds = last_frame.get("analysis", {}).get("wounds", [])

        for casualty_info in top_casualties:
            wounds_raw = _wounds_for_casualty(casualty_info, all_wounds)

            cid = f"A{next_id}"
            next_id += 1

            casualty = _casualty_from_vision(casualty_info, wounds_raw, cid)
            combined.append((casualty, scene_tag))

    return combined


def rank_roster(engine: TriageEngine, casualties: list[Casualty]) -> list[dict]:
    results = []

    for casualty in casualties:
        app_state.upsert_casualty(casualty)

        evidence = engine.gather_evidence(casualty)
        scores = engine.calculate_triage_scores(evidence)
        priority = engine.determine_priority(scores)
        suggestion = engine.analyze_casualty(casualty)

        results.append({
            "casualty_id": casualty.casualty_id,
            "priority": priority,
            "priority_value": priority.value,
            "confidence": suggestion.confidence if suggestion else 0.0,
            "reasoning": suggestion.suggestion if suggestion else "",
            "total_score": scores["total_score"],
        })

    results.sort(key=lambda r: (PRIORITY_RANK[r["priority"]], -r["total_score"]))
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("vision_jsons", nargs="+")
    args = parser.parse_args()

    expanded = []
    for pattern in args.vision_jsons:
        expanded += [Path(p) for p in glob.glob(pattern)]

    casualty_scenes = load_casualties_from_jsons(expanded)
    casualties = [c for c, _ in casualty_scenes]

    app_state._reset_for_tests()
    engine = TriageEngine()

    results = rank_roster(engine, casualties)

    for r in results:
        print(r)


if __name__ == "__main__":
    main()
    