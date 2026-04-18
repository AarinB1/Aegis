from __future__ import annotations

import json

import streamlit as st

from shared.state import app_state


def audit_log() -> None:
    entries = list(reversed(app_state.get_audit_log()))

    with st.expander("Decision History", expanded=False):
        if not entries:
            st.markdown('<div class="aegis-empty">No audit entries yet.</div>', unsafe_allow_html=True)
            return

        for entry in entries[:25]:
            st.markdown(
                (
                    "<div class='aegis-row' style='display:block;'>"
                    f"<div class='aegis-list-title'>{entry.source} · {entry.action}</div>"
                    f"<div class='aegis-list-meta'>{entry.timestamp.isoformat()}</div>"
                    f"<div class='aegis-list-meta' style='margin-top:0.45rem;'>"
                    f"{json.dumps(entry.details, default=str, sort_keys=True)}</div>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
