from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from shared.state import app_state
from ui.components.audit_log import audit_log
from ui.components.controls import controls
from ui.components.pending_panel import pending_panel
from ui.components.roster import roster
from ui.components.sidebar_toggle import render_sidebar_toggle_bridge
from ui.components.video_pane import video_pane
from ui.components.voice_hud import voice_hud
from ui.theme import (
    BACKGROUND,
    BORDER,
    DIVIDER,
    FONT_MONO,
    FONT_SANS,
    FONT_SERIF_DISPLAY,
    GOLD,
    GOLD_SOFT,
    SHADOW,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    SURFACE,
    SURFACE_SOFT,
    TEXT_MUTED,
    TEXT_PRIMARY,
    hud_label,
)


def _ensure_seeded() -> None:
    if not app_state.get_roster():
        from scripts.seed_fake_data import seed

        seed()


STYLE_BLOCK = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400..900;1,400..900&family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600&display=swap');

:root {{
    --bg: {BACKGROUND};
    --surface: {SURFACE};
    --surface-soft: {SURFACE_SOFT};
    --border: {BORDER};
    --divider: {DIVIDER};
    --text-primary: {TEXT_PRIMARY};
    --text-muted: {TEXT_MUTED};
    --gold: {GOLD};
    --gold-soft: {GOLD_SOFT};
    --shadow: {SHADOW};
    --font-serif: {FONT_SERIF_DISPLAY};
    --font-sans: {FONT_SANS};
    --font-mono: {FONT_MONO};
    --space-sm: {SPACE_SM}px;
    --space-md: {SPACE_MD}px;
    --space-lg: {SPACE_LG}px;
    --space-xl: {SPACE_XL}px;
}}

html, body, [class*="css"] {{
    font-family: var(--font-sans);
}}

body {{
    color: var(--text-primary);
}}

.stApp {{
    background: var(--bg);
    color: var(--text-primary);
}}

[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
#MainMenu,
footer {{
    display: none !important;
}}

header[data-testid="stHeader"] {{
    background: transparent;
    pointer-events: none;
}}

[data-testid="stBaseButton-headerNoPadding"] {{
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
    border-radius: 999px;
    border: 1px solid var(--border) !important;
    box-shadow: var(--shadow);
    background: rgba(250, 250, 246, 0.96) !important;
}}

[data-testid="stBaseButton-headerNoPadding"]:hover {{
    background: rgba(184, 130, 15, 0.08) !important;
}}

[data-testid="collapsedControl"] {{
    position: fixed;
    top: 0.9rem;
    left: 0.9rem;
    z-index: 1001;
    border-radius: 999px;
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
    background: rgba(250, 250, 246, 0.96);
}}

[data-testid="stExpandSidebarButton"] {{
    position: fixed;
    top: 0.9rem;
    left: 0.9rem;
    z-index: 1002;
    visibility: visible !important;
    display: inline-flex !important;
    pointer-events: auto !important;
    width: 36px !important;
    height: 36px !important;
    border-radius: 999px;
    border: 1px solid var(--border) !important;
    box-shadow: var(--shadow);
    background: rgba(250, 250, 246, 0.96) !important;
}}

[data-testid="stExpandSidebarButton"]:hover {{
    background: rgba(184, 130, 15, 0.08) !important;
}}

[data-testid="collapsedControl"] button {{
    visibility: visible !important;
    border-radius: 999px;
}}

[data-testid="collapsedControl"] button:hover {{
    background: rgba(184, 130, 15, 0.08);
}}

[data-testid="stAppViewContainer"] {{
    background: var(--bg);
}}

[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #f7f4ed 0%, #f2eee5 100%);
    border-right: 1px solid var(--border);
}}

[data-testid="stSidebar"] .block-container {{
    padding-top: 1.25rem;
    padding-left: 1rem;
    padding-right: 1rem;
}}

.block-container {{
    padding-top: 1.25rem;
    padding-bottom: 2rem;
    max-width: 1400px;
}}

h1, h2, h3, h4, h5, h6,
.display-title,
.display-id,
.serif-display {{
    font-family: var(--font-serif) !important;
    color: var(--text-primary);
    letter-spacing: -0.03em;
}}

.display-title {{
    font-size: clamp(2.2rem, 5vw, 4.35rem);
    line-height: 0.96;
    margin: 0;
    font-weight: 700;
}}

.display-title em,
.editorial-italic {{
    font-style: italic;
    color: #5e5a53;
    font-weight: 500;
}}

code, pre, kbd,
.hud-label,
.hud-meta,
.mono,
.timestamp,
.status-chip,
.source-badge,
.chip,
.timeline-source {{
    font-family: var(--font-mono) !important;
}}

.app-shell {{
    padding-bottom: 1.5rem;
}}

.dashboard-intro {{
    margin-bottom: 1.8rem;
}}

.dashboard-copy {{
    max-width: 58rem;
    color: var(--text-muted);
    font-size: 1rem;
    line-height: 1.65;
}}

.mission-band {{
    margin-top: 1.15rem;
}}

.mission-grid {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 1.3rem;
    margin-top: 1.15rem;
}}

.mission-step {{
    background: rgba(255, 255, 255, 0.45);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.15rem 1.1rem;
    min-height: 100%;
}}

.mission-step-title {{
    font-family: var(--font-serif) !important;
    font-size: 1.18rem;
    line-height: 1.08;
    margin: 0.15rem 0 0;
    color: var(--text-primary);
}}

.mission-step-copy {{
    color: var(--text-muted);
    font-size: 0.92rem;
    line-height: 1.55;
    margin-top: 0.45rem;
}}

.dashboard-lower {{
    margin-top: 1.35rem;
}}

.stack-gap {{
    height: 1rem;
}}

.hud-label {{
    display: inline-block;
    font-size: 0.73rem;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    color: var(--text-muted);
}}

.card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    box-shadow: var(--shadow);
    padding: 1.1rem 1.15rem;
}}

.card-minimal {{
    background: transparent;
    border: 0;
    box-shadow: none;
    padding: 0;
}}

.card-header {{
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1rem;
}}

.card-title {{
    font-family: var(--font-serif) !important;
    font-size: 2rem;
    line-height: 1;
    font-weight: 700;
    margin: 0.1rem 0 0;
}}

.card-kicker {{
    display: inline-block;
    margin-bottom: 0.4rem;
}}

.card-meta {{
    font-family: var(--font-mono);
    font-size: 0.75rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text-muted);
    text-align: right;
    white-space: nowrap;
}}

.card-subtle {{
    color: var(--text-muted);
    font-size: 0.95rem;
    line-height: 1.55;
}}

.triage-dot {{
    font-size: 0.95rem;
    vertical-align: middle;
    margin-right: 0.45rem;
}}

.triage-immediate {{ color: #C8302D; }}
.triage-delayed {{ color: #D4A92B; }}
.triage-minimal {{ color: #3F7C4F; }}
.triage-expectant {{ color: #8A8680; }}
.triage-deceased {{ color: #1C1B1A; }}
.triage-unassessed {{ color: #F5F2EB; text-shadow: 0 0 0 1px #8A8680; }}

.source-dot {{
    font-size: 0.8rem;
    margin-right: 0.35rem;
}}

.status-chip {{
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.3rem 0.65rem;
    color: var(--text-muted);
    font-size: 0.73rem;
    text-transform: uppercase;
    letter-spacing: 0.16em;
}}

.source-badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.72rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text-muted);
}}

.roster-list {{
    border-top: 1px solid var(--divider);
}}

.roster-row {{
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding: 1rem 0.1rem;
    border-bottom: 1px solid var(--divider);
    transition: background 160ms ease;
}}

.roster-row:hover {{
    background: rgba(184, 130, 15, 0.04);
}}

.roster-title {{
    font-family: var(--font-serif) !important;
    font-size: 1.55rem;
    line-height: 1;
    margin: 0;
}}

.roster-row-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    box-shadow: var(--shadow);
    padding: 1rem 1.1rem;
    margin-top: 0.75rem;
    transition: background 160ms ease, transform 160ms ease;
}}

.roster-row-card:hover {{
    background: rgba(184, 130, 15, 0.04);
    transform: translateY(-1px);
}}

.roster-summary {{
    color: var(--text-primary);
    font-size: 0.97rem;
    line-height: 1.45;
    margin-top: 0.28rem;
}}

.roster-meta {{
    color: var(--text-muted);
    font-size: 0.84rem;
    line-height: 1.55;
    margin-top: 0.25rem;
}}

.pending-card {{
    border-top: 1px solid var(--divider);
    padding-top: 1rem;
    margin-top: 1rem;
}}

.pending-top {{
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
}}

.pending-casualty {{
    font-family: var(--font-serif);
    font-size: 1.45rem;
    line-height: 1.05;
    margin: 0.45rem 0 0.35rem;
}}

.pending-text {{
    color: var(--text-primary);
    font-size: 0.98rem;
    line-height: 1.55;
}}

.pending-actions-note {{
    margin-top: 0.65rem;
    color: var(--text-muted);
    font-size: 0.8rem;
    line-height: 1.45;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}}

.pending-meta {{
    color: var(--text-muted);
    font-size: 0.78rem;
    line-height: 1.5;
    margin-top: 0.35rem;
}}

.voice-status {{
    display: flex;
    align-items: center;
    gap: 0.55rem;
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.15em;
    font-size: 0.76rem;
    color: var(--text-primary);
}}

.voice-dot {{
    color: #8A8680;
    font-size: 0.9rem;
}}

.voice-dot.live {{
    color: #3F7C4F;
    animation: aegisPulse 1.4s ease-in-out infinite;
}}

@keyframes aegisPulse {{
    0%, 100% {{ opacity: 1; transform: scale(1); }}
    50% {{ opacity: 0.45; transform: scale(1.18); }}
}}

.voice-transcript {{
    margin-top: 0.9rem;
    padding: 0.85rem 0.95rem;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.35);
}}

.voice-transcript-text {{
    font-family: var(--font-mono);
    font-size: 0.9rem;
    color: var(--text-primary);
}}

.intent-chip {{
    display: inline-flex;
    align-items: center;
    padding: 0.28rem 0.6rem;
    border-radius: 999px;
    border: 1px solid #d8d0bd;
    background: #f4efe4;
    color: #5a5548;
    font-family: var(--font-mono);
    font-size: 0.73rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-top: 0.7rem;
}}

.medevac-head {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    margin-bottom: 0.9rem;
}}

.medevac-row-card {{
    background: rgba(255, 255, 255, 0.4);
    border-top: 1px solid var(--divider);
    padding: 0.85rem 0.1rem;
}}

.medevac-row {{
    display: grid;
    grid-template-columns: minmax(180px, 230px) 1fr;
    gap: 1rem;
    align-items: start;
    padding: 0.8rem 0;
    border-top: 1px solid var(--divider);
}}

.medevac-left {{
    display: flex;
    align-items: center;
    gap: 0.65rem;
}}

.medevac-line {{
    font-family: var(--font-mono);
    font-size: 0.74rem;
    color: var(--text-muted);
    letter-spacing: 0.16em;
    text-transform: uppercase;
    min-width: 2.2rem;
}}

.medevac-label {{
    font-family: var(--font-mono);
    font-size: 0.74rem;
    color: var(--text-muted);
    letter-spacing: 0.16em;
    text-transform: uppercase;
}}

.medevac-value {{
    color: var(--text-primary);
    font-size: 0.98rem;
    line-height: 1.5;
}}

.field-dot {{
    font-size: 0.9rem;
}}

.field-dot.ready {{
    color: #3F7C4F;
}}

.field-dot.waiting {{
    color: #b9b3a5;
}}

.timeline-shell {{
    padding-top: 0.35rem;
}}

.timeline-row {{
    display: grid;
    grid-template-columns: 140px 120px 1fr;
    gap: 1rem;
    align-items: start;
    padding: 0.9rem 0;
    border-top: 1px solid var(--divider);
}}

.timeline-row:first-child {{
    border-top: 0;
}}

.timeline-time {{
    font-family: var(--font-mono);
    font-size: 0.75rem;
    letter-spacing: 0.08em;
    color: var(--text-muted);
}}

.timeline-source {{
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    color: var(--text-muted);
}}

.timeline-action {{
    color: var(--text-primary);
    font-size: 0.95rem;
    line-height: 1.5;
}}

.timeline-details {{
    color: var(--text-muted);
    font-size: 0.8rem;
    line-height: 1.5;
    margin-top: 0.25rem;
}}

.video-frame-card {{
    padding: 1rem;
}}

.video-meta-row {{
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
    margin-bottom: 0.65rem;
}}

.video-meta-row.bottom {{
    margin-top: 0.7rem;
    margin-bottom: 0;
}}

.video-meta-right {{
    text-align: right;
}}

[data-testid="stImage"] img {{
    border-radius: 14px;
    border: 1px solid rgba(26, 26, 26, 0.08);
}}

.video-reid {{
    font-family: var(--font-mono);
    font-size: 0.74rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-muted);
}}

.video-empty {{
    min-height: 420px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    background: linear-gradient(180deg, rgba(250,250,246,0.85) 0%, rgba(245,242,235,0.96) 100%);
}}

.video-empty-glyph {{
    font-size: 3rem;
    color: var(--gold);
    line-height: 1;
    margin-bottom: 0.75rem;
}}

.sidebar-wordmark {{
    display: flex;
    align-items: center;
    gap: 0.45rem;
    margin-bottom: 1rem;
}}

.sidebar-wordmark .diamond {{
    color: var(--gold);
    font-size: 0.9rem;
}}

.sidebar-wordmark .label {{
    font-family: var(--font-serif);
    font-size: 2rem;
    line-height: 1;
    font-weight: 700;
}}

.sidebar-meta {{
    margin-bottom: 1.15rem;
    color: var(--text-muted);
    font-size: 0.92rem;
    line-height: 1.55;
}}

.sidebar-section {{
    margin-top: 1.1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--divider);
}}

.demo-status {{
    margin-top: 0.7rem;
    margin-bottom: 0.9rem;
    padding: 0.75rem 0.85rem;
    border-radius: 12px;
    border: 1px solid var(--border);
    background: rgba(255, 255, 255, 0.36);
    color: var(--text-primary);
    font-family: var(--font-mono);
    font-size: 0.78rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}}

.stButton > button {{
    border-radius: 999px;
    font-family: var(--font-sans);
    font-weight: 500;
    min-height: 2.65rem;
    transition: all 120ms ease;
}}

.stButton > button[kind="primary"] {{
    background: var(--gold);
    color: #fffdf7;
    border: 1px solid var(--gold);
}}

.stButton > button[kind="primary"]:hover {{
    background: #9e700d;
    border-color: #9e700d;
}}

.stButton > button[kind="secondary"] {{
    background: transparent;
    color: var(--text-primary);
    border: 1px solid #d3cbb8;
}}

.stButton > button[kind="secondary"]:hover {{
    background: rgba(184, 130, 15, 0.05);
    border-color: var(--gold);
    color: var(--gold);
}}

.stButton > button[kind="tertiary"] {{
    background: transparent;
    color: var(--text-muted);
    border: 0;
    box-shadow: none;
    text-decoration: underline;
    text-underline-offset: 0.18rem;
}}

.stButton > button[kind="tertiary"]:hover {{
    color: var(--text-primary);
    background: transparent;
}}

div[data-baseweb="select"] > div,
.stToggle label {{
    font-family: var(--font-sans);
}}

.stToggle [data-testid="stWidgetLabel"] {{
    font-family: var(--font-mono);
    letter-spacing: 0.16em;
    text-transform: uppercase;
    font-size: 0.72rem;
}}

@media (max-width: 900px) {{
    .mission-grid {{
        grid-template-columns: 1fr 1fr;
    }}

    .timeline-row {{
        grid-template-columns: 1fr;
        gap: 0.35rem;
    }}

    .medevac-row {{
        grid-template-columns: 1fr;
        gap: 0.45rem;
    }}
}}

@media (max-width: 640px) {{
    .mission-grid {{
        grid-template-columns: 1fr;
    }}
}}
</style>
"""


def _hero() -> None:
    st.markdown(
        f"""
        <div class="dashboard-intro">
            <div class="card-kicker">{hud_label("AI-enhanced guidance for integrated survival")}</div>
            <h1 class="display-title">A shield of perception<br><em>for those who shield others.</em></h1>
            <p class="dashboard-copy">
                AEGIS helps one medic manage many casualties by turning visual wounds,
                respiratory cues, and triage recommendations into one medic-confirmed workflow.
                This view shows what the system sees, what it hears, and what still requires
                human judgment before action.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _mission_band() -> None:
    st.markdown(
        f"""
        <section class="card mission-band">
            <div class="card-header">
                <div>
                    <div class="card-kicker">{hud_label("How to read this dashboard")}</div>
                    <div class="card-title">From chaos to confirmed action</div>
                </div>
                <div class="card-meta">human-in-the-loop triage</div>
            </div>
            <div class="mission-grid">
                <div class="mission-step">
                    <div class="card-kicker">{hud_label("Problem")}</div>
                    <div class="mission-step-title">One medic cannot watch every casualty at once.</div>
                    <div class="mission-step-copy">
                        MASCAL care breaks down when attention is overloaded. The risk is missing a bleed,
                        airway issue, or change in condition while treating someone else.
                    </div>
                </div>
                <div class="mission-step">
                    <div class="card-kicker">{hud_label("Vision")}</div>
                    <div class="mission-step-title">The video feed tracks casualties and visible wounds.</div>
                    <div class="mission-step-copy">
                        Bounding boxes and wound cues surface likely hemorrhage, injury location, and scene-level
                        focus so the medic can see who needs attention first.
                    </div>
                </div>
                <div class="mission-step">
                    <div class="card-kicker">{hud_label("Audio")}</div>
                    <div class="mission-step-title">Breathing and voice cues add what the camera cannot.</div>
                    <div class="mission-step-copy">
                        Respiratory distress, verbal responses, and spoken commands appear below the video to
                        support faster reassessment and hands-free triage.
                    </div>
                </div>
                <div class="mission-step">
                    <div class="card-kicker">{hud_label("Decision")}</div>
                    <div class="mission-step-title">AI recommendations queue for medic confirmation.</div>
                    <div class="mission-step-copy">
                        Nothing critical is auto-applied. The queue on the right is where the medic confirms,
                        dismisses, and turns perception into action.
                    </div>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(page_title="AEGIS Tactical Dashboard", layout="wide", initial_sidebar_state="expanded")
st.markdown(STYLE_BLOCK, unsafe_allow_html=True)
_ensure_seeded()
render_sidebar_toggle_bridge()


@st.fragment(run_every=0.5)
def render_controls() -> None:
    controls()


@st.fragment(run_every=0.5)
def render_dashboard() -> None:
    _hero()

    with st.container():
        video_col, roster_col = st.columns([1.85, 1], gap="large")
        with video_col:
            video_pane()
        with roster_col:
            roster()

    with st.container():
        signal_col, queue_col = st.columns([1, 1], gap="large")
        with signal_col:
            voice_hud()
        with queue_col:
            pending_panel()

    with st.container():
        audit_log()

with st.sidebar:
    render_controls()
render_dashboard()
