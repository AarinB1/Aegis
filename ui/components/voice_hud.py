from __future__ import annotations

import streamlit as st

from shared.state import app_state
from ui.theme import ACCENT_BLUE, GREEN, RED


def _last_voice_decision() -> str:
    for entry in reversed(app_state.get_audit_log()):
        if entry.action == "confirmed_suggestion":
            return "Confirmed"
        if entry.action == "dismissed_suggestion":
            return "Dismissed"
    return "Awaiting action"


def voice_hud() -> None:
    state, transcription = app_state.get_voice_state()
    status_label = _last_voice_decision()
    indicator = GREEN if state == "listening" else RED

    st.markdown(
        '<div class="aegis-panel"><div class="aegis-kicker">Voice</div>'
        '<div class="aegis-title">Voice HUD</div>'
        '<div class="aegis-subtle">Current microphone state and last medic action.</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        (
            "<div class='aegis-row'>"
            "<div>"
            f"<div class='aegis-list-title'>Mic: {transcription or 'idle'}</div>"
            f"<div class='aegis-list-meta'>Recognizer state: {state}</div>"
            "</div>"
            f"<div class='aegis-badge' style='background:{indicator}22;border:1px solid {indicator};"
            f"color:{indicator};'>{state.upper()}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        (
            "<div class='aegis-row'>"
            "<div>"
            "<div class='aegis-list-title'>Last suggestion action</div>"
            "<div class='aegis-list-meta'>Updates from medic confirmation flow.</div>"
            "</div>"
            f"<div class='aegis-badge' style='background:{ACCENT_BLUE}22;border:1px solid {ACCENT_BLUE};"
            f"color:{ACCENT_BLUE};'>{status_label}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
