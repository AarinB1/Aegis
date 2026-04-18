from __future__ import annotations

import html
import json

import streamlit as st

from shared.state import app_state
from ui.theme import hud_label


def _source_label(source: str) -> str:
    if source.lower() == "medic":
        return "MEDIC"
    if source.lower() in {"vision", "audio", "fusion", "ai"}:
        return "AI"
    return "SYSTEM"


def audit_log() -> None:
    entries = list(reversed(app_state.get_audit_log()))
    st.markdown(
        f"""
        <section class="card card-minimal">
            <div class="card-header">
                <div>
                    <div class="card-kicker">{hud_label("Audit Log")}</div>
                    <div class="card-title">Decision History</div>
                </div>
                <div class="card-meta">{len(entries)} entries</div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if not entries:
        st.markdown('<div class="card-subtle">No audit entries yet.</div>', unsafe_allow_html=True)
        return

    for entry in entries[:30]:
        action = entry.action.replace("_", " ")
        details = json.dumps(entry.details, default=str, sort_keys=True)
        st.markdown(
            f"""
            <div class="timeline-row">
                <div class="timeline-time">{html.escape(entry.timestamp.strftime('%H:%M:%S'))}</div>
                <div class="timeline-source">{html.escape(_source_label(entry.source))}</div>
                <div>
                    <div class="timeline-action">{html.escape(action)}</div>
                    <div class="timeline-details">{html.escape(details)}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
