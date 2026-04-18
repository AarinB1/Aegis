from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.state import app_state
from scripts.seed_fake_data import seed
from ui.components.demo_player import DemoPlayer, DemoPlayerError
from ui.theme import hud_label

DEMO_SCENARIOS = {
    "Off": None,
    "Scripted MASCAL (90s)": {
        "video_path": ROOT / "assets" / "test_wound_video.avi",
        "script_path": ROOT / "scripts" / "demo_scenarios" / "mascal_90s.json",
        "duration": 90.0,
    },
}


def _format_demo_seconds(seconds: float) -> str:
    clipped = max(0.0, seconds)
    return f"00:{clipped:04.1f}"


def _get_demo_player() -> DemoPlayer | None:
    player = st.session_state.get("demo_player")
    return player if isinstance(player, DemoPlayer) else None


def _clear_demo_player() -> None:
    st.session_state.pop("demo_player", None)


def _stop_demo_player() -> None:
    player = _get_demo_player()
    if player is not None:
        player.stop()
    _clear_demo_player()


def _status_text(player: DemoPlayer | None, selection: str) -> str:
    if player is None or selection == "Off":
        return "Idle"

    status = player.status
    total = DEMO_SCENARIOS.get(selection, {}).get("duration", player.duration)
    elapsed = _format_demo_seconds(status["t"])
    total_text = _format_demo_seconds(float(total))

    if status["state"] == "playing":
        return f"Playing · {elapsed} / {total_text}"
    if status["state"] == "paused":
        return f"Paused · {elapsed} / {total_text}"
    return "Idle"


def controls() -> None:
    st.markdown(
        f"""
        <div class="sidebar-wordmark">
            <span class="diamond">◆</span>
            <span class="label">AEGIS</span>
        </div>
        <div class="sidebar-meta">
            {hud_label("UI control spine")}<br>
            Editorial surface over the shared tactical state singleton.
        </div>
        """,
        unsafe_allow_html=True,
    )

    current_ai_enabled = app_state.is_ai_enabled()
    ai_enabled = st.toggle("AI Enabled", value=current_ai_enabled)
    if ai_enabled != current_ai_enabled:
        app_state.set_ai_enabled(ai_enabled)
        st.rerun()

    st.markdown(
        f"""
        <div class="sidebar-section">
            <div class="card-kicker">{hud_label("Demo Mode")}</div>
            <div class="sidebar-meta">
                Same-process safety net for rehearsals and live fallback. Play resumes when paused.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    previous_mode = st.session_state.setdefault("_demo_mode_selection", "Off")
    mode_names = list(DEMO_SCENARIOS.keys())
    mode_index = mode_names.index(previous_mode) if previous_mode in mode_names else 0
    demo_mode = st.selectbox("Scenario", mode_names, index=mode_index)
    if demo_mode != previous_mode:
        st.session_state["_demo_mode_selection"] = demo_mode
        st.session_state.pop("demo_error", None)
        app_state.audit("ui", "set_demo_mode", {"mode": demo_mode})
        if demo_mode == "Off":
            _stop_demo_player()
        elif _get_demo_player() is not None:
            _stop_demo_player()
        st.rerun()

    player = _get_demo_player()
    status = player.status if player is not None else {"state": "idle", "t": 0.0}

    play_col, pause_col, stop_col = st.columns(3, gap="small")
    with play_col:
        if st.button("Play", width="stretch"):
            st.session_state.pop("demo_error", None)
            if demo_mode == "Off":
                st.session_state["demo_error"] = "Select a scripted demo before clicking Play."
            elif player is None:
                scenario = DEMO_SCENARIOS[demo_mode]
                try:
                    player = DemoPlayer(
                        video_path=scenario["video_path"],
                        script_path=scenario["script_path"],
                    )
                    st.session_state["demo_player"] = player
                    player.start()
                except DemoPlayerError as exc:
                    st.session_state["demo_error"] = str(exc)
                    _clear_demo_player()
            elif status["state"] == "paused":
                player.resume()
            elif status["state"] == "idle":
                player.start()
            st.rerun()

    with pause_col:
        pause_disabled = player is None or status["state"] != "playing"
        if st.button("Pause", width="stretch", disabled=pause_disabled):
            player.pause()
            st.rerun()

    with stop_col:
        stop_disabled = player is None
        if st.button("Stop", width="stretch", disabled=stop_disabled):
            _stop_demo_player()
            st.rerun()

    st.markdown(
        f'<div class="demo-status">{_status_text(_get_demo_player(), demo_mode)}</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.get("demo_error"):
        st.error(st.session_state["demo_error"])

    if st.button("Reset scenario", type="secondary", width="stretch"):
        _stop_demo_player()
        app_state._reset_for_tests()
        seed()
        st.rerun()

    st.markdown(f'<div class="sidebar-meta">{hud_label("Refresh cadence · 500ms")}</div>', unsafe_allow_html=True)
