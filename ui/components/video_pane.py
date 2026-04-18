from __future__ import annotations

import streamlit as st

from shared.state import app_state
from ui.theme import hud_label


def video_pane() -> None:
    frame = app_state.get_latest_frame()
    roster = app_state.get_roster()
    reid_text = (
        f"re-id · roster synced to {roster[0].casualty_id}"
        if roster
        else "re-id · awaiting roster sync"
    )

    if frame is None:
        st.markdown(
            f"""
            <section class="card video-frame-card">
                <div class="video-empty">
                    <div class="video-empty-glyph">◆</div>
                    <div class="card-kicker">{hud_label("Vision")}</div>
                    <div class="card-title">Video Pane</div>
                    <div class="card-subtle">No feed available from the state spine.</div>
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f"""
        <section class="card video-frame-card">
            <div class="video-meta-row">
                <div>{hud_label("Vision · Frame 00:04:12")}</div>
                <div class="video-meta-right">{hud_label("24.7 FPS · YOLOv8 / ByteTrack")}</div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.image(frame[:, :, ::-1], use_container_width=True)
    st.markdown(
        f"""
        <div class="video-meta-row bottom">
            <div class="video-reid">{reid_text}</div>
            <div class="video-meta-right">{hud_label("Model · Demo Scene")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
