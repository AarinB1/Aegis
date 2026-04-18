# test_triage_engine.py - Real integration tests for Person 3 (Ansh) triage engine
# Tests against the team's actual schema.py and shared/state.py.
# Run: python3 test_triage_engine.py

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from schema import (
    AISuggestion, Casualty, Intervention,
    RespiratoryStatus, TriageCategory, Wound,
)
from shared.state import app_state
from triage_engine import TriageEngine


def _reset():
    app_state._reset_for_tests()


def _print_header(text):
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def _print_result(label, passed, detail=""):
    mark = "PASS" if passed else "FAIL"
    line = f"[{mark}] {label}"
    if detail:
        line += f"  --  {detail}"
    print(line)


def _make_casualty(casualty_id, wounds, *,
                   respiratory_status=RespiratoryStatus.NORMAL,
                   respiratory_rate=16, responsive=True,
                   triage_category=TriageCategory.UNASSESSED):
    return Casualty(
        casualty_id=casualty_id,
        triage_category=triage_category,
        responsive=responsive,
        respiratory_status=respiratory_status,
        respiratory_rate=respiratory_rate,
        wounds=wounds,
    )


def test_red_severe_bleeding_thigh():
    _reset()
    engine = TriageEngine()
    casualty = _make_casualty("A1", wounds=[
        Wound(location="right_thigh", area_cm2=33.0, severity="severe",
              active_bleeding=True, ai_confidence=0.9)
    ])
    app_state.upsert_casualty(casualty)
    evidence = engine.gather_evidence(casualty)
    scores = engine.calculate_triage_scores(evidence)
    priority = engine.determine_priority(scores)
    _print_result("Severe bleeding thigh -> IMMEDIATE",
                  priority == TriageCategory.IMMEDIATE,
                  f"priority={priority.value}, total={scores['total_score']:.1f}")
    return priority == TriageCategory.IMMEDIATE


def test_red_head_wound():
    _reset()
    engine = TriageEngine()
    casualty = _make_casualty("A2", wounds=[
        Wound(location="head", area_cm2=8.0, severity="moderate",
              active_bleeding=True, ai_confidence=0.85)
    ])
    app_state.upsert_casualty(casualty)
    evidence = engine.gather_evidence(casualty)
    scores = engine.calculate_triage_scores(evidence)
    priority = engine.determine_priority(scores)
    _print_result("Head wound with bleeding -> IMMEDIATE",
                  priority == TriageCategory.IMMEDIATE,
                  f"priority={priority.value}, location_score={scores['location_score']}")
    return priority == TriageCategory.IMMEDIATE


def test_yellow_moderate_chest():
    _reset()
    engine = TriageEngine()
    casualty = _make_casualty("A3", wounds=[
        Wound(location="left_chest", area_cm2=6.3, severity="moderate",
              active_bleeding=False, ai_confidence=0.82)
    ], respiratory_rate=20)
    app_state.upsert_casualty(casualty)
    evidence = engine.gather_evidence(casualty)
    scores = engine.calculate_triage_scores(evidence)
    priority = engine.determine_priority(scores)
    _print_result("Moderate chest, stable -> DELAYED",
                  priority == TriageCategory.DELAYED,
                  f"priority={priority.value}, total={scores['total_score']:.1f}")
    return priority == TriageCategory.DELAYED


def test_green_minor_limb():
    _reset()
    engine = TriageEngine()
    casualty = _make_casualty("A4", wounds=[
        Wound(location="right_forearm", area_cm2=2.0, severity="minor",
              active_bleeding=False, ai_confidence=0.75)
    ])
    app_state.upsert_casualty(casualty)
    evidence = engine.gather_evidence(casualty)
    scores = engine.calculate_triage_scores(evidence)
    priority = engine.determine_priority(scores)
    _print_result("Minor limb wound -> MINIMAL",
                  priority == TriageCategory.MINIMAL,
                  f"priority={priority.value}, total={scores['total_score']:.1f}")
    return priority == TriageCategory.MINIMAL


def test_never_expectant():
    _reset()
    engine = TriageEngine()
    casualty = _make_casualty("A5", wounds=[
        Wound(location="head", area_cm2=50.0, severity="severe",
              active_bleeding=True, ai_confidence=0.95),
        Wound(location="chest", area_cm2=40.0, severity="severe",
              active_bleeding=True, ai_confidence=0.95),
    ], respiratory_status=RespiratoryStatus.ABSENT,
       respiratory_rate=0, responsive=False)
    evidence = engine.gather_evidence(casualty)
    scores = engine.calculate_triage_scores(evidence)
    priority = engine.determine_priority(scores)
    is_safe = priority not in (TriageCategory.EXPECTANT, TriageCategory.DECEASED)
    _print_result("Never auto-suggests EXPECTANT/DECEASED", is_safe,
                  f"worst-case priority={priority.value}")
    return is_safe


def test_analyze_casualty_creates_suggestion():
    _reset()
    engine = TriageEngine()
    casualty = _make_casualty("A6", wounds=[
        Wound(location="right_thigh", area_cm2=33.0, severity="severe",
              active_bleeding=True, ai_confidence=0.9)
    ])
    app_state.upsert_casualty(casualty)
    suggestion = engine.analyze_casualty(casualty)
    passed = (suggestion is not None
              and isinstance(suggestion, AISuggestion)
              and 0.0 <= suggestion.confidence <= 1.0
              and len(casualty.ai_suggestions_log) >= 1)
    detail = f"confidence={suggestion.confidence:.2f}, source={suggestion.source}" if suggestion else "none"
    _print_result("analyze_casualty produces AISuggestion", passed, detail)
    if suggestion:
        print(f"       Llama reasoning: {suggestion.suggestion}")
    return passed


def test_process_all_casualties_flow():
    _reset()
    engine = TriageEngine()
    casualties = [
        _make_casualty("B1", [Wound(location="head", area_cm2=8.0, severity="severe",
                                    active_bleeding=True, ai_confidence=0.9)]),
        _make_casualty("B2", [Wound(location="left_arm", area_cm2=3.0, severity="minor",
                                    active_bleeding=False, ai_confidence=0.7)]),
        _make_casualty("B3", [Wound(location="abdomen", area_cm2=10.0, severity="moderate",
                                    active_bleeding=True, ai_confidence=0.85)]),
    ]
    for c in casualties:
        app_state.upsert_casualty(c)
    engine.process_all_casualties()
    pending = app_state.get_pending_suggestions()
    triage_suggestions = [s for s in pending if "triage" in s.source.lower()]
    passed = len(triage_suggestions) >= 3
    _print_result("process_all_casualties -> 1 suggestion per casualty",
                  passed, f"{len(triage_suggestions)}/3 suggestions created")
    return passed


def test_audio_suggestion_no_crash():
    _reset()
    engine = TriageEngine()
    casualty = _make_casualty("D1", wounds=[
        Wound(location="chest", area_cm2=5.0, severity="moderate",
              active_bleeding=False, ai_confidence=0.8)
    ])
    app_state.upsert_casualty(casualty)
    app_state.add_suggestion(AISuggestion(
        timestamp=datetime.now(timezone.utc),
        source="audio",
        suggestion="D1: Detected AIRWAY COMPROMISE - stridor pattern",
        confidence=0.87,
    ))
    try:
        suggestion = engine.analyze_casualty(casualty)
        passed = suggestion is not None
        _print_result("Handles audio suggestions without crashing", passed)
        return passed
    except Exception as e:
        _print_result("Handles audio suggestions without crashing", False, str(e))
        return False


def test_priority_counts():
    _reset()
    engine = TriageEngine()
    app_state.upsert_casualty(_make_casualty("R1", [Wound(location="thigh", area_cm2=10,
        severity="minor", active_bleeding=False, ai_confidence=0.8)],
        triage_category=TriageCategory.IMMEDIATE))
    app_state.upsert_casualty(_make_casualty("R2", [Wound(location="arm", area_cm2=5,
        severity="minor", active_bleeding=False, ai_confidence=0.8)],
        triage_category=TriageCategory.DELAYED))
    app_state.upsert_casualty(_make_casualty("R3", [Wound(location="forearm", area_cm2=2,
        severity="minor", active_bleeding=False, ai_confidence=0.8)],
        triage_category=TriageCategory.MINIMAL))
    counts_str = engine.get_patient_priority_counts()
    passed = all(x in counts_str for x in ["RED: 1", "YELLOW: 1", "GREEN: 1"])
    _print_result("Priority counts match roster", passed, counts_str)
    return passed


def test_medevac_9_line():
    _reset()
    engine = TriageEngine()
    casualty = _make_casualty("C1", wounds=[
        Wound(location="neck", area_cm2=5.0, severity="severe",
              active_bleeding=True, ai_confidence=0.9)
    ], triage_category=TriageCategory.IMMEDIATE)
    app_state.upsert_casualty(casualty)
    nine_line = engine.generate_medevac_9_line("C1")
    required = [f"line_{i}_" for i in range(1, 10)]
    has_all = all(any(k.startswith(r) for k in nine_line.keys()) for r in required)
    equip = nine_line.get("line_4_special_equipment", "")
    has_equip = "BLOOD PRODUCTS" in equip and "AIRWAY MANAGEMENT" in equip
    active = app_state.get_active_medevac()
    medevac_set = active is not None and active["casualty_id"] == "C1"
    passed = has_all and has_equip and medevac_set
    _print_result("MEDEVAC 9-line generation", passed, f"equipment='{equip}'")
    if passed:
        print("\n       Generated 9-line:")
        for k in sorted(nine_line.keys()):
            if k.startswith("line_"):
                print(f"          {k}: {nine_line[k]}")
    return passed


def test_medevac_missing():
    _reset()
    engine = TriageEngine()
    result = engine.generate_medevac_9_line("DOES_NOT_EXIST")
    passed = result == {}
    _print_result("MEDEVAC for unknown casualty returns {}", passed)
    return passed


def main():
    print("TRIAGE ENGINE - FULL INTEGRATION TEST SUITE")
    print("(testing against team's schema.py + shared/state.py)")

    _print_header("TRIAGE CLASSIFICATION")
    r = []
    r.append(test_red_severe_bleeding_thigh())
    r.append(test_red_head_wound())
    r.append(test_yellow_moderate_chest())
    r.append(test_green_minor_limb())

    _print_header("SAFETY INVARIANTS")
    r.append(test_never_expectant())

    _print_header("APPSTATE INTEGRATION")
    r.append(test_analyze_casualty_creates_suggestion())
    r.append(test_process_all_casualties_flow())
    r.append(test_audio_suggestion_no_crash())
    r.append(test_priority_counts())

    _print_header("MEDEVAC")
    r.append(test_medevac_9_line())
    r.append(test_medevac_missing())

    _print_header("SUMMARY")
    passed = sum(r)
    total = len(r)
    print(f"\n  {passed} / {total} tests passed")
    if passed == total:
        print("  ALL TESTS PASSED - ready for team integration\n")
        return 0
    print(f"  {total - passed} tests failed - review output above\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
