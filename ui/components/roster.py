from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from schema import TriageCategory
from shared.state import app_state
from ui.theme import triage_color, triage_label

TRIAGE_ORDER = {
    TriageCategory.IMMEDIATE: 0,
    TriageCategory.DELAYED: 1,
    TriageCategory.MINIMAL: 2,
    TriageCategory.EXPECTANT: 3,
    TriageCategory.DECEASED: 4,
    TriageCategory.UNASSESSED: 5,
}


def _seconds_since(timestamp: datetime) -> int:
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return max(0, int((datetime.now(timezone.utc) - timestamp).total_seconds()))


def roster() -> None:
    casualties = sorted(
        app_state.get_roster(),
        key=lambda casualty: (TRIAGE_ORDER.get(casualty.triage_category, 99), casualty.casualty_id),
    )

    st.markdown(
        '<div class="aegis-panel"><div class="aegis-kicker">Tracking</div>'
        '<div class="aegis-title">Casualty Roster</div>'
        '<div class="aegis-subtle">Live casualty state from the shared app singleton.</div></div>',
        unsafe_allow_html=True,
    )

    if not casualties:
        st.markdown('<div class="aegis-empty">No casualties in state.</div>', unsafe_allow_html=True)
        return

    for casualty in casualties:
        color = triage_color(casualty.triage_category)
        badge_style = (
            f"background:{color}22;border:1px solid {color};color:{color};"
            "box-shadow:0 0 18px rgba(0,0,0,0.15) inset;"
        )
        responsive = (
            "responsive"
            if casualty.responsive is True
            else "unresponsive"
            if casualty.responsive is False
            else "unknown response"
        )
        st.markdown(
            (
                f"<div class='aegis-row' style='border-left:4px solid {color};'>"
                "<div>"
                f"<div class='aegis-list-title'>{casualty.casualty_id}</div>"
                f"<div class='aegis-list-meta'>{casualty.posture} · {responsive}</div>"
                f"<div class='aegis-list-meta'>"
                f"Wounds {len(casualty.wounds)} · Resp {casualty.respiratory_status.value}"
                f" · Seen {_seconds_since(casualty.last_seen)}s ago"
                "</div></div>"
                f"<div class='aegis-badge' style='{badge_style}'>{triage_label(casualty.triage_category)}</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
