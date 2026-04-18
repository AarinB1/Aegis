from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.state import app_state
from scripts.seed_fake_data import seed
from ui.theme import hud_label

DEMO_MODES = ["Pre-recorded", "Webcam", "Fake"]


def controls() -> None:
    with st.sidebar:
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

        previous_mode = st.session_state.setdefault("_demo_mode", "Fake")
        mode_index = DEMO_MODES.index(previous_mode) if previous_mode in DEMO_MODES else 2
        demo_mode = st.selectbox("Demo mode", DEMO_MODES, index=mode_index)
        if demo_mode != previous_mode:
            st.session_state["_demo_mode"] = demo_mode
            app_state.audit("ui", "set_demo_mode", {"mode": demo_mode})
            st.rerun()

        if st.button("Reset scenario", type="secondary", width="stretch"):
            app_state._reset_for_tests()
            seed()
            st.rerun()

        st.markdown(f'<div class="sidebar-meta">{hud_label("Refresh cadence · 500ms")}</div>', unsafe_allow_html=True)
