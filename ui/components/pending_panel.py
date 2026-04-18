from __future__ import annotations

import streamlit as st

from shared.state import app_state
from ui.theme import source_color


def pending_panel() -> None:
    pending_suggestions = sorted(
        app_state.get_pending_suggestions(),
        key=lambda pending: pending.created_at,
        reverse=True,
    )

    st.markdown(
        '<div class="aegis-panel"><div class="aegis-kicker">Review Queue</div>'
        '<div class="aegis-title">Pending AI</div>'
        '<div class="aegis-subtle">AI outputs are wrapped in PendingSuggestion before medic action.</div></div>',
        unsafe_allow_html=True,
    )

    if not pending_suggestions:
        st.markdown('<div class="aegis-empty">No pending suggestions.</div>', unsafe_allow_html=True)
        return

    for pending in pending_suggestions:
        badge = source_color(pending.source)
        casualty_id = pending.casualty_id or "Unknown casualty"
        raw_text = getattr(pending.raw, "suggestion", "No suggestion text")

        st.markdown(
            (
                "<div class='aegis-row' style='display:block;'>"
                "<div style='display:flex;justify-content:space-between;align-items:center;gap:0.75rem;'>"
                f"<div class='aegis-badge' style='background:{badge}22;border:1px solid {badge};color:{badge};'>"
                f"{pending.source.title()}</div>"
                f"<div class='aegis-list-meta'>{casualty_id}</div>"
                "</div>"
                f"<div class='aegis-list-title' style='margin-top:0.7rem;'>{raw_text}</div>"
                f"<div class='aegis-list-meta'>Pending ID: {pending.id}</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        st.progress(max(0.0, min(1.0, pending.confidence)))
        st.caption(f"Confidence {pending.confidence:.2f}")
        confirm_col, dismiss_col = st.columns(2)
        with confirm_col:
            if st.button("✓ Confirm", key=f"confirm-{pending.id}", width="stretch"):
                app_state.confirm_suggestion(pending.id)
                st.rerun()
        with dismiss_col:
            if st.button("✗ Dismiss", key=f"dismiss-{pending.id}", width="stretch"):
                app_state.dismiss_suggestion(pending.id)
                st.rerun()
