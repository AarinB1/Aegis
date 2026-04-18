"""
scenario_ranker.py - Multi-casualty, multi-scene triage ranker

Accepts one or more vision JSON files produced by Suri's pipeline
(scripts/run_judge_demo.py). Each JSON contributes one or more casualties
to a combined roster, which Ansh's SALT/TCCC engine + Llama 3.2 then
ranks by evacuation priority.

Usage:
    # Single scene
    python3 scenario_ranker.py outputs/judge_demo/hero/*_video_wounds.json

    # Multi-scene MASCAL
    python3 scenario_ranker.py \
        outputs/judge_demo/hero/*_video_wounds.json \
        outputs/judge_demo/indoor/*_video_wounds.json \
        outputs/judge_demo/torso/*_video_wounds.json
"""

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
    """Derive a short scene tag (e.g. 'hero', 'indoor', 'torso') from the
    JSON path so we can disambiguate casualties across scenes."""
    parts = json_path.parts
    if "judge_demo" in parts:
        idx = parts.index("judge_demo")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return json_path.stem[:10]


def _wounds_for_casualty(casualty_info: dict, all_wounds: list[dict]) -> list[dict]:
    """Assign wounds to a casualty by bbox containment of the wound center."""
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
    # Single-casualty scene: claim all wounds if none matched by bbox
    if not matched and casualty_info.get("wound_count", 0) > 0:
        matched = all_wounds
    return matched


def _casualty_from_vision(
    casualty_info: dict,
    wounds_raw: list[dict],
    casualty_id: str,
) -> Casualty:
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

    # Vision detected wounds but none could be mapped to this casualty's bbox
    if not wounds and casualty_info.get("wound_count", 0) > 0:
        wounds.append(
            Wound(
                location="limb",
                area_cm2=5.0,
                severity=_severity_label(
                    float(casualty_info.get("overall_severity", 0.5))
                ),
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
    """
    Load all casualties from a list of Suri-style vision JSONs.
    Returns list of (Casualty, source_scene_tag) pairs.
    Casualties are renamed A1, A2, A3... across the combined roster so
    per-scene name collisions don't hide anyone.
    """
    combined: list[tuple[Casualty, str]] = []
    next_id = 1

    for json_path in json_paths:
        scene_tag = _scene_tag_from_path(json_path)
        try:
            vision_data = json.loads(json_path.read_text())
        except Exception as e:
            print(f"  [skip] {json_path}: failed to parse ({e})")
            continue

        frames = vision_data.get("frames", [])
        if not frames:
            print(f"  [skip] {json_path}: no frames")
            continue

        last_frame = frames[-1]
        top_casualties = last_frame.get("scene_summary", {}).get("top_casualties", [])
        all_wounds = last_frame.get("analysis", {}).get("wounds", [])

        if not top_casualties:
            print(f"  [skip] {json_path}: no casualties in scene_summary")
            continue

        for casualty_info in top_casualties:
            wounds_raw = _wounds_for_casualty(casualty_info, all_wounds)
            new_id = f"A{next_id}"
            next_id += 1
            casualty = _casualty_from_vision(casualty_info, wounds_raw, new_id)
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
            "wound_count": len(casualty.wounds),
            "bleeding_any": any(w.active_bleeding for w in casualty.wounds),
            "total_score": scores["total_score"],
            "bleeding_score": scores["bleeding_score"],
            "location_score": scores["location_score"],
            "respiratory_score": scores["respiratory_score"],
            "top_wound_location": casualty.wounds[0].location if casualty.wounds else "none",
        })

    results.sort(key=lambda r: (PRIORITY_RANK[r["priority"]], -r["total_score"]))
    return results


def print_ranking(results: list[dict], scene_tags: dict[str, str]) -> None:
    if not results:
        print("\nNo casualties found in vision data.")
        return

    print("\n" + "=" * 78)
    print("MASCAL MULTI-CASUALTY TRIAGE RANKING")
    print("  (Suri's vision pipeline  ->  Ansh's SALT/TCCC engine  ->  Llama 3.2)")
    print("=" * 78)

    priority_symbol = {
        "red": "[RED]   ",
        "yellow": "[YELLOW]",
        "green": "[GREEN] ",
        "white": "[WHITE] ",
        "gray": "[GRAY]  ",
        "black": "[BLACK] ",
    }

    for idx, r in enumerate(results, 1):
        sym = priority_symbol.get(r["priority_value"], "[?]     ")
        scene = scene_tags.get(r["casualty_id"], "unknown")
        print(f"\n#{idx}  {sym}  casualty={r['casualty_id']}  "
              f"(scene: {scene})  "
              f"confidence={r['confidence']:.2f}  score={r['total_score']:.1f}")
        print(f"        wounds={r['wound_count']}  "
              f"bleeding={'YES' if r['bleeding_any'] else 'no'}  "
              f"location={r['top_wound_location']}  "
              f"bleed_score={r['bleeding_score']:.1f}  "
              f"loc_score={r['location_score']}")
        if r["reasoning"]:
            print(f"        reasoning: {r['reasoning']}")

    print("\n" + "=" * 78)
    print(f"EVACUATION ORDER: {'  ->  '.join(r['casualty_id'] for r in results)}")
    priority_counts = {}
    for r in results:
        priority_counts[r["priority_value"]] = priority_counts.get(r["priority_value"], 0) + 1
    summary = ", ".join(f"{v.upper()}: {k}" for v, k in priority_counts.items())
    print(f"ROSTER: {summary}")
    print("=" * 78 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Multi-casualty triage ranker fusing Suri's vision JSONs with Ansh's engine + Llama"
    )
    parser.add_argument(
        "vision_jsons",
        nargs="+",
        help="One or more vision JSON paths (globs OK: 'outputs/judge_demo/**/*.json')",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and print extracted casualties, skip triage scoring")
    args = parser.parse_args()

    # Expand globs (shell may not expand them when using */*.json patterns)
    expanded_paths: list[Path] = []
    for pattern in args.vision_jsons:
        matches = glob.glob(pattern, recursive=True)
        if matches:
            expanded_paths.extend(Path(m) for m in matches)
        else:
            p = Path(pattern)
            if p.exists():
                expanded_paths.append(p)
            else:
                print(f"  [warn] no match for: {pattern}")

    if not expanded_paths:
        print("ERROR: no vision JSONs found. Try:")
        print("  python3 scripts/run_judge_demo.py hero --allow-builtin-yolo --skip-reel")
        sys.exit(1)

    print(f"Loading {len(expanded_paths)} vision JSON(s):")
    for p in expanded_paths:
        print(f"  - {p}")

    casualty_scenes = load_casualties_from_jsons(expanded_paths)
    casualties = [c for c, _ in casualty_scenes]
    scene_tags = {c.casualty_id: tag for c, tag in casualty_scenes}

    print(f"\nExtracted {len(casualties)} casualty(ies) across {len(expanded_paths)} scene(s)")

    if args.dry_run:
        print("\n--- DRY RUN (no triage scoring) ---")
        for c in casualties:
            print(f"  {c.casualty_id} (scene: {scene_tags[c.casualty_id]}): "
                  f"{len(c.wounds)} wound(s)")
            for w in c.wounds:
                print(f"    - {w.location}: severity={w.severity}, "
                      f"bleeding={w.active_bleeding}, area={w.area_cm2:.1f}cm2")
        return

    if not casualties:
        print("No casualties to rank.")
        sys.exit(1)

    app_state._reset_for_tests()
    engine = TriageEngine()
    results = rank_roster(engine, casualties)
    print_ranking(results, scene_tags)


if __name__ == "__main__":
    main()
