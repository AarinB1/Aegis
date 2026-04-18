from __future__ import annotations

import streamlit as st

from shared.state import app_state
from ui.theme import TEXT_MUTED


def video_pane() -> None:
    frame = app_state.get_latest_frame()

    st.markdown(
        '<div class="aegis-panel"><div class="aegis-kicker">Live Scene</div>'
        '<div class="aegis-title">Video Pane</div>'
        '<div class="aegis-subtle">Placeholder surface for the incoming video transport.</div></div>',
        unsafe_allow_html=True,
    )

    if frame is None:
        st.markdown(
            '<div class="aegis-video-shell"><div class="aegis-empty">'
            "No feed available. Waiting for the next frame from the state spine."
            "</div></div>",
            unsafe_allow_html=True,
        )
        return

    st.markdown('<div class="aegis-video-shell">', unsafe_allow_html=True)
    st.image(frame, channels="BGR", width="stretch")
    st.markdown(
        (
            f"<div style='display:flex;justify-content:space-between;color:{TEXT_MUTED};"
            f"font-size:0.8rem;padding-top:0.35rem;'>"
            "<span>Feed status: demo frame</span>"
            f"<span>Frame shape: {frame.shape[1]} x {frame.shape[0]}</span>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
