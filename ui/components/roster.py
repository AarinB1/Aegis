from __future__ import annotations

from datetime import datetime, timezone
import html

import streamlit as st

from schema import TriageCategory
from shared.state import app_state
from ui.theme import hud_label, triage_dot, triage_label

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
        f"""
        <section class="card">
            <div class="card-header">
                <div>
                    <div class="card-kicker">{hud_label("Casualty Roster")}</div>
                    <div class="card-title">Roster</div>
                </div>
                <div class="card-meta">{len(casualties)} tracked</div>
            </div>
            <div class="card-subtle">Live casualty roster synchronized to the shared state spine.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if not casualties:
        st.markdown(
            '<div class="card-subtle" style="margin-top:0.9rem;">No casualties in state.</div>',
            unsafe_allow_html=True,
        )
        return

    for casualty in casualties:
        wound_summary = "No wounds logged" if not casualty.wounds else ", ".join(
            wound.location.replace("_", " ") for wound in casualty.wounds[:2]
        )
        responsive = (
            "responsive"
            if casualty.responsive is True
            else "unresponsive"
            if casualty.responsive is False
            else "response unknown"
        )
        st.markdown(
            f"""
            <article class="roster-row-card">
                <div class="roster-row">
                    <div>
                        <div class="roster-title">{triage_dot(casualty.triage_category)}Casualty #{html.escape(casualty.casualty_id)}</div>
                        <div class="roster-summary">{html.escape(wound_summary)}</div>
                        <div class="roster-meta">
                            {html.escape(casualty.posture)} · {html.escape(responsive)} ·
                            resp {html.escape(casualty.respiratory_status.value)} · seen {_seconds_since(casualty.last_seen)}s ago
                        </div>
                    </div>
                    <div class="card-meta">
                        {html.escape(triage_label(casualty.triage_category))}<br>
                        wounds {len(casualty.wounds)}
                    </div>
                </div>
            </article>
            """,
            unsafe_allow_html=True,
        )
