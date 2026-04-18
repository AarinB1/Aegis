from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from shared.state import app_state
from ui.components.audit_log import audit_log
from ui.components.controls import controls
from ui.components.medevac import medevac
from ui.components.pending_panel import pending_panel
from ui.components.roster import roster
from ui.components.video_pane import video_pane
from ui.components.voice_hud import voice_hud
from ui.theme import GLOBAL_CSS


def _ensure_seeded() -> None:
    if not app_state.get_roster():
        from scripts.seed_fake_data import seed

        seed()


st.set_page_config(page_title="AEGIS Tactical Dashboard", layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
_ensure_seeded()
controls()


@st.fragment(run_every=0.5)
def render_dashboard() -> None:
    st.markdown("## AEGIS MASCAL Perception System")
    st.caption("UI layer bound to the live `schema.py` and `shared/state.py` contract.")

    with st.container():
        video_col, roster_col = st.columns([1.75, 1], gap="large")
        with video_col:
            video_pane()
        with roster_col:
            roster()

    with st.container():
        voice_col, pending_col = st.columns([1.2, 1], gap="large")
        with voice_col:
            voice_hud()
        with pending_col:
            pending_panel()

    with st.container():
        medevac()

    with st.container():
        audit_log()


render_dashboard()
