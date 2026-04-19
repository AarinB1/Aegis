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
from ui.components.live_vision_player import DEFAULT_HERO_VIDEO, LiveVisionPlayer, LiveVisionPlayerError
from ui.components.simulation_seeder import clear_simulation_assets, get_simulation_assets, seed_simulation
from ui.theme import hud_label

DEMO_SCENARIOS = {
    "Off": None,
    "Scripted MASCAL (90s)": {
        "video_path": ROOT / "assets" / "test_wound_video.avi",
        "script_path": ROOT / "scripts" / "demo_scenarios" / "mascal_90s.json",
        "duration": 90.0,
    },
    "Live Vision": {
        "video_path": DEFAULT_HERO_VIDEO,
        "duration": None,
    },
    "Simulation (mixed)": {
        "duration": None,
        "static": True,
    },
}

PLAYER_TYPES = (DemoPlayer, LiveVisionPlayer)


def _format_demo_seconds(seconds: float) -> str:
    clipped = max(0.0, seconds)
    return f"00:{clipped:04.1f}"


def _get_demo_player() -> DemoPlayer | LiveVisionPlayer | None:
    player = st.session_state.get("demo_player")
    return player if isinstance(player, PLAYER_TYPES) else None


def _clear_demo_player() -> None:
    st.session_state.pop("demo_player", None)


def _stop_demo_player() -> None:
    player = _get_demo_player()
    if player is not None:
        player.stop()
    _clear_demo_player()


def _status_text(player: DemoPlayer | LiveVisionPlayer | None, selection: str) -> str:
    if player is None or selection == "Off":
        return "Idle"

    status = player.status
    scenario = DEMO_SCENARIOS.get(selection) or {}
    total = scenario.get("duration")
    if total is None and hasattr(player, "duration"):
        total = getattr(player, "duration")
    elapsed = _format_demo_seconds(status["t"])
    total_text = _format_demo_seconds(float(total)) if total is not None else None

    if status["state"] == "playing":
        if total_text is None:
            return f"Playing · {elapsed}"
        return f"Playing · {elapsed} / {total_text}"
    if status["state"] == "paused":
        if total_text is None:
            return f"Paused · {elapsed}"
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

    st.markdown(
        f"""
        <div class="sidebar-section" style="margin-top:0;padding-top:0;border-top:0;">
            <div class="card-kicker">{hud_label("Navigation")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/1_Dashboard.py", label="◆ Dashboard", use_container_width=True)
    st.page_link("pages/2_Tactical_Map.py", label="Tactical Map", use_container_width=True)

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
                Same-process safety net for rehearsals and live fallback. Scripted mode stays intact while Live Vision runs the real pipeline through the shared state spine.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    inferred_simulation = bool(get_simulation_assets())
    if "_demo_mode_selection" not in st.session_state:
        st.session_state["_demo_mode_selection"] = "Simulation (mixed)" if inferred_simulation else "Off"
    if "_scenario_state" not in st.session_state:
        st.session_state["_scenario_state"] = "simulation" if inferred_simulation else "bootstrap"

    previous_mode = st.session_state["_demo_mode_selection"]
    mode_names = list(DEMO_SCENARIOS.keys())
    mode_index = mode_names.index(previous_mode) if previous_mode in mode_names else 0
    demo_mode = st.selectbox("Scenario", mode_names, index=mode_index)
    if demo_mode != previous_mode:
        st.session_state["_demo_mode_selection"] = demo_mode
        st.session_state.pop("demo_error", None)
        app_state.audit("ui", "set_demo_mode", {"mode": demo_mode})
        if st.session_state.get("_scenario_state") == "simulation":
            app_state._reset_for_tests()
            clear_simulation_assets()
            st.session_state["_scenario_state"] = "off"
            st.session_state["selected_id"] = None
            st.query_params.clear()
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
            elif demo_mode == "Simulation (mixed)":
                _stop_demo_player()
                app_state._reset_for_tests()
                seed()
                seed_simulation(include_existing=True)
                st.session_state["_scenario_state"] = "simulation"
                st.session_state["selected_id"] = None
                st.query_params.clear()
            elif player is None:
                scenario = DEMO_SCENARIOS[demo_mode]
                try:
                    if demo_mode == "Scripted MASCAL (90s)":
                        player = DemoPlayer(
                            video_path=scenario["video_path"],
                            script_path=scenario["script_path"],
                        )
                        st.session_state["_scenario_state"] = "scripted"
                    elif demo_mode == "Live Vision":
                        app_state._reset_for_tests()
                        player = LiveVisionPlayer(video_path=scenario["video_path"])
                        st.session_state["_scenario_state"] = "live_vision"
                    else:
                        raise DemoPlayerError(f"Unsupported demo mode: {demo_mode}")
                    st.session_state["demo_player"] = player
                    player.start()
                except (DemoPlayerError, LiveVisionPlayerError) as exc:
                    st.session_state["demo_error"] = str(exc)
                    _clear_demo_player()
            elif status["state"] == "paused":
                player.resume()
            elif status["state"] == "idle":
                player.start()
            st.rerun()

    with pause_col:
        pause_disabled = player is None or status["state"] != "playing" or demo_mode == "Live Vision"
        if st.button("Pause", width="stretch", disabled=pause_disabled):
            player.pause()
            st.rerun()

    with stop_col:
        stop_disabled = player is None and st.session_state.get("_scenario_state") != "simulation"
        if st.button("Stop", width="stretch", disabled=stop_disabled):
            if st.session_state.get("_scenario_state") == "simulation":
                _stop_demo_player()
                app_state._reset_for_tests()
                clear_simulation_assets()
                st.session_state["_demo_mode_selection"] = "Off"
                st.session_state["_scenario_state"] = "off"
                st.session_state["selected_id"] = None
                st.query_params.clear()
            else:
                _stop_demo_player()
            st.rerun()

    st.markdown(
        f'<div class="demo-status">{_status_text(_get_demo_player(), demo_mode)}</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.get("demo_error"):
        st.error(st.session_state["demo_error"])

    if st.button("Reset scenario", type="secondary", width="stretch"):
        if demo_mode == "Simulation (mixed)" or st.session_state.get("_scenario_state") == "simulation":
            _stop_demo_player()
            app_state._reset_for_tests()
            clear_simulation_assets()
            st.session_state["_demo_mode_selection"] = "Off"
            st.session_state["_scenario_state"] = "off"
            st.session_state["selected_id"] = None
            st.query_params.clear()
        else:
            _stop_demo_player()
            app_state._reset_for_tests()
            seed()
            st.session_state["_scenario_state"] = "baseline"
        st.rerun()

    st.markdown(f'<div class="sidebar-meta">{hud_label("Refresh cadence · 500ms")}</div>', unsafe_allow_html=True)
