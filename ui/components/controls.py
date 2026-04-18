from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.state import app_state
from scripts.seed_fake_data import reset_and_seed

DEMO_MODES = ["Pre-recorded", "Webcam", "Fake"]


def controls() -> None:
    with st.sidebar:
        st.markdown("### Controls")

        current_ai_enabled = app_state.is_ai_enabled()
        ai_enabled = st.toggle(
            "AI Enabled",
            value=current_ai_enabled,
            help="Routes confirmable AI suggestions into the pending review panel.",
        )
        if ai_enabled != current_ai_enabled:
            app_state.set_ai_enabled(ai_enabled)
            st.rerun()

        previous_mode = st.session_state.setdefault("_demo_mode", "Fake")
        default_index = DEMO_MODES.index(previous_mode) if previous_mode in DEMO_MODES else 2
        demo_mode = st.selectbox("Demo mode", DEMO_MODES, index=default_index)
        if demo_mode != previous_mode:
            st.session_state["_demo_mode"] = demo_mode
            app_state.audit("ui", "set_demo_mode", {"mode": demo_mode})
            st.rerun()

        if st.button("Reset scenario", type="primary", width="stretch"):
            reset_and_seed()
            st.rerun()

        st.caption("Dashboard autorefresh: 500ms")
