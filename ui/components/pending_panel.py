from __future__ import annotations

import streamlit as st

from shared.state import app_state
from ui.theme import source_color


def _payload_summary(payload: dict) -> str:
    if not payload:
        return "No additional payload"

    parts = []
    for key, value in payload.items():
        if hasattr(value, "value"):
            value = value.value
        parts.append(f"{key}={value}")
    return " · ".join(parts)


def pending_panel() -> None:
    suggestions = sorted(
        app_state.get_pending_suggestions(),
        key=lambda suggestion: suggestion.created_at,
        reverse=True,
    )

    st.markdown(
        '<div class="aegis-panel"><div class="aegis-kicker">Review Queue</div>'
        '<div class="aegis-title">Pending AI</div>'
        '<div class="aegis-subtle">Medic confirmation gate for cross-component actions.</div></div>',
        unsafe_allow_html=True,
    )

    if not suggestions:
        st.markdown('<div class="aegis-empty">No pending suggestions.</div>', unsafe_allow_html=True)
        return

    for suggestion in suggestions:
        badge = source_color(suggestion.source)
        st.markdown(
            (
                "<div class='aegis-row' style='display:block;'>"
                "<div style='display:flex;justify-content:space-between;align-items:center;gap:0.75rem;'>"
                f"<div class='aegis-badge' style='background:{badge}22;border:1px solid {badge};color:{badge};'>"
                f"{suggestion.source.title()}</div>"
                f"<div class='aegis-list-meta'>{suggestion.casualty_id}</div>"
                "</div>"
                f"<div class='aegis-list-title' style='margin-top:0.7rem;'>{suggestion.kind}</div>"
                f"<div class='aegis-list-meta'>{_payload_summary(suggestion.payload)}</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        st.progress(suggestion.confidence)
        st.caption(f"Confidence {suggestion.confidence:.2f}")
        confirm_col, dismiss_col = st.columns(2)
        with confirm_col:
            if st.button(
                "✓ Confirm",
                key=f"confirm-{suggestion.id}",
                width="stretch",
            ):
                app_state.confirm_suggestion(suggestion.id)
                st.rerun()
        with dismiss_col:
            if st.button(
                "✗ Dismiss",
                key=f"dismiss-{suggestion.id}",
                width="stretch",
            ):
                app_state.dismiss_suggestion(suggestion.id)
                st.rerun()
