from __future__ import annotations

from datetime import datetime, timezone
import html

import streamlit as st

from shared.state import app_state
from ui.theme import hud_label, source_dot


def _pending_created_at(pending) -> float:
    created_at = getattr(pending, "created_at", None)
    if not isinstance(created_at, datetime):
        return 0.0
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at.timestamp()


def _clean_suggestion_text(raw_text: str, casualty_id: str) -> str:
    prefix = f"{casualty_id}:"
    text = str(raw_text).strip()
    if text.startswith(prefix):
        return text[len(prefix):].strip()
    return text


def _truncate(text: str, limit: int) -> str:
    value = " ".join(str(text).split())
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + "..."


def pending_panel() -> None:
    pending_suggestions = sorted(
        app_state.get_pending_suggestions(),
        key=_pending_created_at,
        reverse=True,
    )

    st.markdown(
        f"""
        <section class="card">
            <div class="card-header">
                <div>
                    <div class="card-kicker">{hud_label("Human-in-the-loop")}</div>
                    <div class="card-title">Medic Confirmation Queue</div>
                </div>
                <div class="card-meta">{len(pending_suggestions)} active</div>
            </div>
            <div class="card-subtle">
                Every AI-generated recommendation lands here first. The medic confirms or
                dismisses each item before it changes care or triage.
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

    if not pending_suggestions:
        return

    active_pending = pending_suggestions[0]
    upcoming_pending = pending_suggestions[1:]

    active_raw_text = getattr(active_pending.raw, "suggestion", "No suggestion text")
    active_casualty_id = active_pending.casualty_id or "unlinked"
    active_text = _clean_suggestion_text(active_raw_text, active_casualty_id)
    active_confidence = round(max(0.0, min(1.0, active_pending.confidence)) * 100)

    st.markdown(
        f"""
        <div class="pending-section-label">{hud_label("Next Action")}</div>
        <article class="card pending-featured-card">
            <div class="pending-top">
                <div>
                    <div class="source-badge">{source_dot(active_pending.source)}{html.escape(active_pending.source.upper())}</div>
                    <div class="pending-casualty">Casualty #{html.escape(active_casualty_id)}</div>
                </div>
                <div class="card-meta">AI · {active_confidence}%</div>
            </div>
            <div class="pending-text">{html.escape(active_text)}</div>
            <div class="pending-actions-note">Highest priority confirmation</div>
            <div class="pending-meta">Pending ID {html.escape(active_pending.id)}</div>
        </article>
        """,
        unsafe_allow_html=True,
    )
    confirm_col, dismiss_col = st.columns([1.2, 0.8], gap="small")
    with confirm_col:
        if st.button("Confirm", key=f"confirm-{active_pending.id}", type="primary", width="stretch"):
            app_state.confirm_suggestion(active_pending.id)
            st.rerun()
    with dismiss_col:
        if st.button("Dismiss", key=f"dismiss-{active_pending.id}", type="secondary", width="stretch"):
            app_state.dismiss_suggestion(active_pending.id)
            st.rerun()

    if not upcoming_pending:
        st.markdown(
            f'<div class="pending-quiet-note">{hud_label("Upcoming")} Queue clear after this action.</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f"""
        <div class="pending-upcoming-head">
            <div class="pending-section-label">{hud_label("Upcoming")}</div>
            <div class="card-meta">{len(upcoming_pending)} queued</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for pending in upcoming_pending:
        raw_text = getattr(pending.raw, "suggestion", "No suggestion text")
        casualty_id = pending.casualty_id or "unlinked"
        summary = _truncate(_clean_suggestion_text(raw_text, casualty_id), 78)
        confidence = round(max(0.0, min(1.0, pending.confidence)) * 100)
        row_col, confirm_col, dismiss_col = st.columns([3.95, 1.55, 0.9], gap="small")
        with row_col:
            st.markdown(
                f"""
                <div class="pending-upcoming-row">
                    <div class="pending-upcoming-copy">
                        <div class="pending-upcoming-topline">
                            <div class="source-badge">{source_dot(pending.source)}{html.escape(pending.source.upper())}</div>
                            <div class="pending-upcoming-confidence">{confidence}%</div>
                        </div>
                        <div class="pending-upcoming-casualty">Casualty #{html.escape(casualty_id)}</div>
                        <div class="pending-upcoming-summary">{html.escape(summary)}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with confirm_col:
            if st.button("Confirm", key=f"confirm-{pending.id}", type="secondary", width="content"):
                app_state.confirm_suggestion(pending.id)
                st.rerun()
        with dismiss_col:
            if st.button("Dismiss", key=f"dismiss-{pending.id}", type="tertiary", width="content"):
                app_state.dismiss_suggestion(pending.id)
                st.rerun()
