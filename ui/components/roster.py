from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from schema import TriageCategory
from shared.state import app_state
from ui.theme import triage_color, triage_label


def _seconds_since(timestamp: datetime) -> int:
    return max(0, int((datetime.now(timezone.utc) - timestamp).total_seconds()))


def roster() -> None:
    casualties = sorted(
        app_state.get_roster(),
        key=lambda casualty: (casualty.triage.value != TriageCategory.RED.value, casualty.id),
    )

    st.markdown(
        '<div class="aegis-panel"><div class="aegis-kicker">Tracking</div>'
        '<div class="aegis-title">Casualty Roster</div>'
        '<div class="aegis-subtle">Live triage state from the shared app singleton.</div></div>',
        unsafe_allow_html=True,
    )

    if not casualties:
        st.markdown('<div class="aegis-empty">No casualties in state.</div>', unsafe_allow_html=True)
        return

    for casualty in casualties:
        color = triage_color(casualty.triage)
        badge_style = (
            f"background:{color}22;border:1px solid {color};color:{color};"
            "box-shadow:0 0 18px rgba(0,0,0,0.15) inset;"
        )
        st.markdown(
            (
                f"<div class='aegis-row' style='border-left:4px solid {color};'>"
                f"<div><div class='aegis-list-title'>{casualty.id}</div>"
                f"<div class='aegis-list-meta'>"
                f"Track {casualty.track_id if casualty.track_id is not None else 'n/a'}"
                f" · Wounds {len(casualty.wounds)} · Seen {_seconds_since(casualty.last_seen)}s ago"
                f"</div></div>"
                f"<div class='aegis-badge' style='{badge_style}'>{triage_label(casualty.triage)}</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
