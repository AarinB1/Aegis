from __future__ import annotations

import html

import streamlit as st

from shared.state import app_state
from ui.theme import hud_label

NINE_LINE_FIELDS = [
    ("line_1", "Location"),
    ("line_2", "Freq / Callsign"),
    ("line_3", "Patients by precedence"),
    ("line_4", "Special equipment"),
    ("line_5", "Patients by type"),
    ("line_6", "Security at PZ"),
    ("line_7", "Marking method"),
    ("line_8", "Nationality / Status"),
    ("line_9", "NBC contamination"),
]


def medevac() -> None:
    active = app_state.get_active_medevac()

    if active is None:
        st.markdown(
            f"""
            <section class="card">
                <div class="card-header">
                    <div>
                        <div class="card-kicker">{hud_label("Evacuation handoff")}</div>
                        <div class="card-title">9-Line Evacuation Draft</div>
                    </div>
                    <div class="card-meta">draft · unavailable</div>
                </div>
                <div class="card-subtle">
                    Confirmed triage and treatment details roll up here for evacuation handoff.
                    No active packet is staged in the state spine yet.
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )
        st.button("Review & confirm", key="medevac-review-empty", type="primary", width="stretch", disabled=True)
        return

    casualty_id = active.get("casualty_id", "Unknown")
    nine_line = active.get("nine_line", {})

    st.markdown(
        f"""
        <section class="card">
            <div class="medevac-head">
                <div>
                    <div class="card-kicker">{hud_label("Evacuation handoff")}</div>
                    <div class="card-title">9-Line Evacuation Draft · {html.escape(casualty_id)}</div>
                </div>
                <div class="card-meta">DRAFT · unconfirmed</div>
            </div>
            <div class="card-subtle">
                Review the drafted handoff packet before transmission. This keeps evacuation details
                tied to the same confirmed casualty record.
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    for index, (key, label) in enumerate(NINE_LINE_FIELDS, start=1):
        value = str(nine_line.get(key, "awaiting input"))
        ready = value.strip() not in {"", "--"} and "awaiting" not in value.lower()
        indicator = "●" if ready else "○"
        st.markdown(
            f"""
            <div class="medevac-row-card">
                <div class="medevac-row">
                    <div class="medevac-left">
                        <span class="field-dot {'ready' if ready else 'waiting'}">{indicator}</span>
                        <span class="medevac-line">{index:02d}</span>
                        <span class="medevac-label">{html.escape(label)}</span>
                    </div>
                    <div class="medevac-value">{html.escape(value)}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.button("Review & confirm", key="medevac-review", type="primary", width="stretch")
