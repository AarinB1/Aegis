from __future__ import annotations

import sys

import streamlit as st

from shared.state import app_state
from scripts.seed_fake_data import seed
from ui.components.demo_catalog import menu_demo_scenarios
from ui.components.demo_player import DemoPlayer, DemoPlayerError
from ui.components.simulation_seeder import clear_simulation_assets, get_simulation_assets
from ui.theme import hud_label

DEMO_SCENARIOS = menu_demo_scenarios()

PLAYER_TYPES = (DemoPlayer,)


def _format_demo_seconds(seconds: float) -> str:
    clipped = max(0.0, seconds)
    return f"00:{clipped:04.1f}"


def _get_demo_player() -> DemoPlayer | None:
    player = st.session_state.get("demo_player")
    return player if isinstance(player, PLAYER_TYPES) else None


def _clear_demo_player() -> None:
    st.session_state.pop("demo_player", None)


def _stop_demo_player() -> None:
    player = _get_demo_player()
    if player is not None:
        player.stop()
    _clear_demo_player()


def _normalize_removed_simulation_state() -> None:
    if not get_simulation_assets() and st.session_state.get("_scenario_state") != "simulation":
        return

    _stop_demo_player()
    clear_simulation_assets()
    app_state._reset_for_tests()
    seed()
    st.session_state["_demo_mode_selection"] = "Off"
    st.session_state["_scenario_state"] = "baseline"
    st.session_state["selected_id"] = None
    st.query_params.clear()


def _status_text(player: DemoPlayer | None, selection: str) -> str:
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
            {hud_label("Curated demo controls")}<br>
            Judge-facing controls for the strongest scripted flow now, with room to slot in a few approved demo clips later.
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
                Switch between the primary outdoor casualty clip and the indoor treatment backup while keeping the same scripted demo flow and shared state.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _normalize_removed_simulation_state()

    if "_demo_mode_selection" not in st.session_state:
        st.session_state["_demo_mode_selection"] = "Off"
    if "_scenario_state" not in st.session_state:
        st.session_state["_scenario_state"] = "bootstrap"

    previous_mode = st.session_state["_demo_mode_selection"]
    mode_names = list(DEMO_SCENARIOS.keys())
    if previous_mode not in mode_names:
        previous_mode = "Off"
        st.session_state["_demo_mode_selection"] = previous_mode
    mode_index = mode_names.index(previous_mode)
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
                    st.session_state["_scenario_state"] = "scripted"
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
            st.session_state["_scenario_state"] = "off"
            st.rerun()

    st.markdown(
        f'<div class="demo-status">{_status_text(_get_demo_player(), demo_mode)}</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.get("demo_error"):
        st.error(st.session_state["demo_error"])

    if st.button("Reset scenario", type="secondary", width="stretch"):
        _stop_demo_player()
        clear_simulation_assets()
        app_state._reset_for_tests()
        seed()
        st.session_state["_scenario_state"] = "baseline"
        st.session_state["selected_id"] = None
        st.query_params.clear()
        st.rerun()

    st.markdown(f'<div class="sidebar-meta">{hud_label("Refresh cadence · 500ms")}</div>', unsafe_allow_html=True)
