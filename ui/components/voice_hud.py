from __future__ import annotations

import html

import streamlit as st

from shared.state import app_state
from ui.theme import hud_label


def _last_voice_decision() -> str:
    for entry in reversed(app_state.get_audit_log()):
        if entry.action == "confirmed_suggestion":
            return "Confirmed"
        if entry.action == "dismissed_suggestion":
            return "Dismissed"
    return "Awaiting action"


def voice_hud() -> None:
    state, transcription = app_state.get_voice_state()
    intent_chip = transcription.strip() if transcription.strip() else "awaiting input"
    live = state.lower() == "listening"

    st.markdown(
        f"""
        <section class="card">
            <div class="card-header">
                <div>
                    <div class="card-kicker">{hud_label("Voice")}</div>
                    <div class="card-title">Acoustics</div>
                </div>
                <div class="card-meta">{html.escape(_last_voice_decision())}</div>
            </div>
            <div class="voice-status">
                <span class="voice-dot {'live' if live else ''}">●</span>
                {html.escape(state.upper())}
            </div>
            <div class="voice-transcript">
                <div class="voice-transcript-text">{html.escape(transcription or 'No active transcription')}</div>
                <div class="intent-chip">{html.escape(intent_chip)}</div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
