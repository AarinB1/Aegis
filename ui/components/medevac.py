from __future__ import annotations

import copy

import streamlit as st

from shared.state import app_state

NINE_LINE_FIELDS = [
    ("line_1", "Location"),
    ("line_2", "Radio"),
    ("line_3", "Precedence"),
    ("line_4", "Special Equip"),
    ("line_5", "Patients"),
    ("line_6", "Security"),
    ("line_7", "Marking"),
    ("line_8", "Nationality"),
    ("line_9", "Terrain"),
]


def _current_medevac() -> dict | None:
    with app_state._lock:
        active = copy.deepcopy(app_state._active_medevac)
    return active


def medevac() -> None:
    active = _current_medevac()
    if not active:
        return

    nine_line = active.get("nine_line", {})
    casualty_id = active.get("casualty_id", "Unknown")

    st.markdown(
        '<div class="aegis-panel"><div class="aegis-kicker">Evacuation</div>'
        f'<div class="aegis-title">9-Line MEDEVAC · {casualty_id}</div>'
        '<div class="aegis-subtle">Visible only when a medevac packet is active.</div></div>',
        unsafe_allow_html=True,
    )
    for row_start in range(0, len(NINE_LINE_FIELDS), 3):
        columns = st.columns(3, gap="medium")
        for column, (key, label) in zip(columns, NINE_LINE_FIELDS[row_start : row_start + 3]):
            value = nine_line.get(key, "--")
            with column:
                st.markdown(
                    (
                        "<div class='aegis-medevac-item'>"
                        f"<div class='aegis-medevac-label'>{label}</div>"
                        f"<div class='aegis-medevac-value'>{value}</div>"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
