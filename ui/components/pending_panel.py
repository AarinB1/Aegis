from __future__ import annotations

import html

import streamlit as st

from shared.state import app_state
from ui.theme import hud_label, source_dot


def pending_panel() -> None:
    pending_suggestions = sorted(
        app_state.get_pending_suggestions(),
        key=lambda pending: pending.created_at,
        reverse=True,
    )

    st.markdown(
        f"""
        <section class="card">
            <div class="card-header">
                <div>
                    <div class="card-kicker">{hud_label("Pending AI")}</div>
                    <div class="card-title">Suggestions</div>
                </div>
                <div class="card-meta">{len(pending_suggestions)} active</div>
            </div>
            {
                '<div class="card-subtle">No pending suggestions.</div>'
                if not pending_suggestions
                else ''
            }
        </section>
        """,
        unsafe_allow_html=True,
    )

    for pending in pending_suggestions:
        raw_text = getattr(pending.raw, "suggestion", "No suggestion text")
        casualty_id = pending.casualty_id or "unlinked"
        confidence = round(max(0.0, min(1.0, pending.confidence)) * 100)
        st.markdown(
            f"""
            <article class="card" style="margin-top:0.9rem;">
                <div class="pending-top">
                    <div>
                        <div class="source-badge">{source_dot(pending.source)}{html.escape(pending.source.upper())}</div>
                        <div class="pending-casualty">Casualty #{html.escape(casualty_id)}</div>
                    </div>
                    <div class="card-meta">AI · {confidence}%</div>
                </div>
                <div class="pending-text">{html.escape(raw_text)}</div>
                <div class="pending-meta">Pending ID {html.escape(pending.id)}</div>
            </article>
            """,
            unsafe_allow_html=True,
        )
        confirm_col, dismiss_col = st.columns([1, 1], gap="small")
        with confirm_col:
            if st.button("Confirm", key=f"confirm-{pending.id}", type="primary", width="stretch"):
                app_state.confirm_suggestion(pending.id)
                st.rerun()
        with dismiss_col:
            if st.button("Dismiss", key=f"dismiss-{pending.id}", type="tertiary", width="stretch"):
                app_state.dismiss_suggestion(pending.id)
                st.rerun()
