from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import html
import math
from pathlib import Path
import re
import sys
from types import MethodType
from urllib.parse import quote

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scenario_ranker as scenario_ranker_module
from scenario_ranker import rank_roster
from schema import AISuggestion, Casualty, TriageCategory
from shared.state import app_state
from scripts.seed_fake_data import seed
from triage_engine import start_triage_engine
from ui.components.controls import controls
from ui.components.demo_catalog import get_medic_pov_clip, sample_curated_frame
from ui.components.sidebar_toggle import render_sidebar_toggle_bridge
from ui.components.simulation_seeder import get_simulation_assets, resolve_sim_asset
from ui.theme import (
    BACKGROUND,
    BORDER,
    DIVIDER,
    FONT_MONO,
    FONT_SANS,
    FONT_SERIF_DISPLAY,
    GOLD,
    GREEN,
    RED,
    AMBER,
    GRAY,
    SHADOW,
    SURFACE,
    SURFACE_SOFT,
    TEXT_MUTED,
    TEXT_PRIMARY,
    triage_label,
)

MAP_WIDTH = 1000
MAP_HEIGHT = 600
SAFE_PADDING = 56
COMPOUND_LEFT = 220
COMPOUND_TOP = 180
COMPOUND_RIGHT = 640
COMPOUND_BOTTOM = 420
MEDIC_COVERAGE_RADIUS = 180
MEDIC_ZONE_RADIUS = 200
UNASSIGNED_DISTANCE = 250
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}

MEDICS = (
    {"id": "MEDIC_HAYES", "label": "MEDIC · SGT HAYES", "name": "SGT HAYES", "x": 350, "y": 280, "css": "medic-one"},
    {"id": "MEDIC_RIOS", "label": "MEDIC · CPL RIOS", "name": "CPL RIOS", "x": 650, "y": 340, "css": "medic-two"},
)

TRIAGE_MARK_STYLES = {
    TriageCategory.IMMEDIATE: {"fill": RED, "stroke": "#FAFAF6"},
    TriageCategory.DELAYED: {"fill": AMBER, "stroke": "#FAFAF6"},
    TriageCategory.MINIMAL: {"fill": GREEN, "stroke": "#FAFAF6"},
    TriageCategory.EXPECTANT: {"fill": GRAY, "stroke": "#FAFAF6"},
    TriageCategory.DECEASED: {"fill": TEXT_PRIMARY, "stroke": "#FAFAF6"},
    TriageCategory.UNASSESSED: {"fill": "none", "stroke": GRAY},
}

LOCAL_PRIORITY_RANK = {
    TriageCategory.IMMEDIATE: 0,
    TriageCategory.DELAYED: 1,
    TriageCategory.MINIMAL: 2,
    TriageCategory.UNASSESSED: 3,
    TriageCategory.EXPECTANT: 4,
    TriageCategory.DECEASED: 5,
}

PRIORITY_VALUE_TO_CATEGORY = {
    "red": TriageCategory.IMMEDIATE,
    "yellow": TriageCategory.DELAYED,
    "green": TriageCategory.MINIMAL,
    "white": TriageCategory.UNASSESSED,
    "gray": TriageCategory.EXPECTANT,
    "black": TriageCategory.DECEASED,
}

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
    --shadow: {SHADOW};
    --font-serif: {FONT_SERIF_DISPLAY};
    --font-sans: {FONT_SANS};
    --font-mono: {FONT_MONO};
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
    padding-left: 1rem;
    padding-right: 1rem;
    max-width: 1780px;
}}

.hud-label,
.mono,
.timestamp,
.status-chip,
.card-meta,
.section-kicker {{
    font-family: var(--font-mono) !important;
}}

.hud-label {{
    display: inline-block;
    font-size: 0.73rem;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    color: var(--text-muted);
}}

.card-kicker {{
    display: inline-block;
    margin-bottom: 0.4rem;
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
    min-height: 2.6rem;
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

div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    box-shadow: var(--shadow);
}}

div[data-testid="stVerticalBlockBorderWrapper"] > div {{
    padding: 0.9rem 1rem 1rem;
}}

.map-card svg {{
    display: block;
}}

.map-toolbar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    margin-bottom: 0.9rem;
}}

.map-toolbar-copy {{
    color: var(--text-muted);
    font-size: 0.9rem;
    line-height: 1.45;
}}

.map-reset-link {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 112px;
    padding: 0.48rem 0.82rem;
    border-radius: 999px;
    border: 1px solid rgba(184, 130, 15, 0.45);
    color: var(--gold);
    text-decoration: none;
    font-family: var(--font-mono);
    font-size: 0.7rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    white-space: nowrap;
}}

.map-reset-link:hover {{
    background: rgba(184, 130, 15, 0.06);
}}

.map-shell {{
    width: 100%;
    aspect-ratio: 1000 / 600;
}}

.map-shell svg {{
    width: 100%;
    height: 100%;
    display: block;
    border-radius: 12px;
}}

.map-link {{
    cursor: pointer;
    text-decoration: none;
}}

.map-label,
.map-status,
.map-grid-label,
.map-corner,
.map-footer,
.medic-label {{
    font-family: var(--font-mono);
    fill: var(--text-primary);
}}

.map-grid-label,
.map-status,
.map-footer {{
    font-size: 11px;
    fill: var(--text-muted);
    letter-spacing: 0.1em;
    text-transform: uppercase;
}}

.map-label,
.medic-label {{
    font-size: 10px;
    letter-spacing: 0.08em;
}}

.quadrant-label {{
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    fill: rgba(26, 26, 26, 0.3);
}}

.hover-glow {{
    opacity: 0;
    transition: opacity 150ms ease;
    pointer-events: none;
}}

.map-contact:hover .hover-glow,
.medic-group:hover .hover-glow {{
    opacity: 0.14;
}}

.pulse-ring,
.selected-reticle,
.priority-reticle,
.ping-ring {{
    transform-origin: center;
    transform-box: fill-box;
    pointer-events: none;
}}

.pulse-ring {{
    animation: pulseRing 1.2s ease-out infinite;
    opacity: 0.82;
}}

.reticle-rotate {{
    animation: reticleSpin 10s linear infinite;
}}

.priority-reticle {{
    opacity: 0.2;
    animation-duration: 22s;
}}

.ping-ring {{
    animation: suggestionPing 0.8s ease-out 1;
}}

.tooltip-fo {{
    opacity: 0;
    transform: translateY(3px);
    transition: opacity 150ms ease, transform 150ms ease;
    pointer-events: none;
}}

.map-contact:hover .tooltip-fo {{
    opacity: 1;
    transform: translateY(0);
}}

.tooltip-card {{
    background: #FAFAF6;
    border: 1px solid #E8E4D8;
    border-radius: 8px;
    padding: 10px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    width: 220px;
    min-height: 92px;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
}}

.tooltip-title {{
    font-family: var(--font-serif);
    font-size: 14px;
    color: var(--text-primary);
    line-height: 1.1;
}}

.tooltip-triage,
.tooltip-meta,
.tooltip-audio,
.mono-line,
.detail-kicker,
.detail-rank,
.stub-label {{
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.14em;
}}

.tooltip-triage,
.tooltip-audio {{
    font-size: 10px;
    color: var(--text-primary);
}}

.tooltip-meta {{
    font-size: 10px;
    color: var(--text-muted);
    text-align: right;
}}

.tooltip-copy {{
    font-size: 11px;
    line-height: 1.4;
    color: var(--text-muted);
}}

.tooltip-dot,
.triage-dot {{
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 999px;
    margin-right: 0.35rem;
    vertical-align: middle;
}}

.detail-kicker {{
    color: var(--text-muted);
    font-size: 0.72rem;
    margin-bottom: 0.45rem;
}}

.detail-title {{
    font-family: var(--font-serif);
    font-size: 2rem;
    line-height: 1;
    margin: 0;
    color: var(--text-primary);
}}

.detail-title.small {{
    font-size: 1.55rem;
}}

.detail-copy {{
    color: var(--text-muted);
    font-size: 0.95rem;
    line-height: 1.6;
}}

.detail-divider {{
    margin: 1rem 0;
    border-top: 1px solid var(--divider);
}}

.identity-line {{
    display: flex;
    align-items: center;
    gap: 0.55rem;
    font-family: var(--font-mono);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    font-size: 0.76rem;
    margin-top: 0.7rem;
}}

.detail-rank,
.mono-line {{
    font-size: 0.76rem;
    color: var(--text-muted);
    margin-top: 0.7rem;
}}

.vision-row,
.intervention-row,
.info-row,
.queue-row,
.zone-row {{
    display: flex;
    align-items: flex-start;
    gap: 0.65rem;
    padding: 0.6rem 0;
    border-top: 1px solid rgba(225, 220, 205, 0.72);
}}

.vision-row:first-of-type,
.intervention-row:first-of-type,
.info-row:first-of-type,
.zone-row:first-of-type {{
    border-top: 0;
    padding-top: 0.1rem;
}}

.vision-meta,
.intervention-meta,
.info-meta {{
    margin-left: auto;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-muted);
    white-space: nowrap;
}}

.italic-diagnosis,
.rationale-copy {{
    font-family: var(--font-serif);
    font-style: italic;
    color: #5f5a52;
}}

.italic-diagnosis {{
    font-size: 1rem;
    line-height: 1.6;
    margin-top: 0.45rem;
}}

.rationale-copy {{
    font-size: 13px;
    line-height: 1.6;
    margin-top: 0.45rem;
}}

.audio-stub {{
    opacity: 0.4;
}}

.audio-slot {{
    border: 1px solid rgba(232, 228, 216, 0.9);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.38);
    margin-top: 0.6rem;
    display: flex;
    align-items: center;
    justify-content: center;
}}

.audio-slot.waveform {{
    min-height: 60px;
    position: relative;
}}

.audio-slot.waveform::before {{
    content: "";
    position: absolute;
    left: 1rem;
    right: 1rem;
    height: 1px;
    background: rgba(122, 118, 104, 0.45);
}}

.audio-slot.compact {{
    min-height: 30px;
    justify-content: flex-start;
    padding: 0 0.9rem;
}}

.audio-awaiting {{
    margin-top: 0.7rem;
    text-align: right;
    font-family: var(--font-mono);
    font-size: 0.7rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--text-muted);
}}

.status-bar {{
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
    margin-top: 0.9rem;
    padding-top: 0.9rem;
    border-top: 1px solid rgba(225, 220, 205, 0.6);
}}

.status-pill,
.march-meta,
.queue-subtitle,
.queue-select,
.zone-select,
.clip-meta,
.hint-copy {{
    font-family: var(--font-mono);
}}

.status-pill,
.march-meta {{
    font-size: 0.76rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}}

.queue-title {{
    font-family: var(--font-serif);
    font-size: 1.25rem;
    line-height: 1;
    margin: 0;
}}

.queue-subtitle,
.zone-meta,
.clip-meta,
.hint-copy {{
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-muted);
}}

.queue-list {{
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
}}

.queue-row {{
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    position: relative;
    column-gap: 0.8rem;
    padding: 0.82rem 0.88rem;
    min-width: 0;
    border: 1px solid rgba(232, 228, 216, 0.95);
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.46);
}}

.queue-row,
.queue-row * {{
    word-break: normal;
    overflow-wrap: normal;
}}

.queue-row.top {{
    background: rgba(184, 130, 15, 0.08);
    border-color: rgba(184, 130, 15, 0.22);
}}

.queue-row.selected {{
    outline: 1px solid rgba(184, 130, 15, 0.45);
    outline-offset: -1px;
    border-radius: 12px;
}}

.queue-leading {{
    display: inline-flex;
    align-items: center;
    gap: 0.65rem;
    min-width: max-content;
}}

.queue-rank {{
    min-width: 2ch;
    color: #7A7668;
    font-family: var(--font-mono);
    font-size: 14px;
    letter-spacing: 0.12em;
    line-height: 1;
    text-align: right;
}}

.queue-dot {{
    width: 12px;
    height: 12px;
    border-radius: 999px;
}}

.queue-main {{
    min-width: 0;
    display: grid;
    gap: 0.2rem;
}}

.queue-name {{
    font-family: var(--font-sans);
    font-size: 15px;
    line-height: 1.25;
    font-weight: 600;
    white-space: normal;
    word-break: keep-all;
    overflow-wrap: normal;
}}

.queue-track {{
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    white-space: nowrap;
}}

.queue-summary {{
    color: var(--text-muted);
    font-size: 11px;
    line-height: 1.45;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    white-space: normal;
    overflow-wrap: anywhere;
}}

.queue-select,
.zone-select {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.45rem 0.72rem;
    border-radius: 999px;
    border: 1px solid rgba(184, 130, 15, 0.45);
    color: var(--gold);
    text-decoration: none;
    white-space: nowrap;
    font-size: 0.7rem;
    transition: all 120ms ease;
}}

.queue-select {{
    min-width: 78px;
    justify-self: end;
    align-self: center;
    padding: 0.42rem 0.68rem;
}}

.queue-select:hover,
.zone-select:hover {{
    background: rgba(184, 130, 15, 0.06);
    border-color: var(--gold);
}}

.empty-panel {{
    color: var(--text-muted);
    min-height: 160px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    border: 1px dashed rgba(184, 130, 15, 0.25);
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.32);
}}

.medic-feed-empty {{
    margin-top: 0.6rem;
    min-height: 280px;
    height: 280px;
    border: 1px solid #E8E4D8;
    border-radius: 12px;
    background: #FAFAF6;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 1.25rem;
}}

.medic-feed-empty-inner {{
    max-width: 260px;
}}

.medic-feed-glyph {{
    font-family: var(--font-mono);
    font-size: 0.95rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: rgba(122, 118, 104, 0.4);
    margin-bottom: 0.55rem;
}}

.medic-feed-kicker {{
    font-family: var(--font-mono);
    font-size: 14px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #7A7668;
}}

.medic-feed-copy {{
    margin-top: 8px;
    font-size: 12px;
    line-height: 1.55;
    color: #7A7668;
}}

.audio-empty {{
    margin-top: 0.65rem;
    border: 1px solid #E8E4D8;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.42);
    padding: 0.9rem 1rem;
}}

.audio-empty-title {{
    font-family: var(--font-mono);
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-muted);
}}

.audio-empty-copy {{
    margin-top: 0.38rem;
    color: var(--text-muted);
    font-size: 0.88rem;
    line-height: 1.5;
}}

@media (max-width: 1180px) {{
    .queue-select {{
        min-width: 72px;
    }}
}}

@media (max-width: 900px) {{
    .map-shell {{
        aspect-ratio: auto;
    }}

    .map-shell svg {{
        height: auto;
    }}
}}

.placeholder-box {{
    min-height: 200px;
    margin-top: 0.6rem;
}}

.map-note,
.note-copy {{
    color: var(--text-muted);
    font-size: 0.86rem;
    line-height: 1.55;
}}

.medic-patrol {{
    transform-box: fill-box;
    transform-origin: center;
    animation-duration: 10s;
    animation-iteration-count: infinite;
    animation-timing-function: ease-in-out;
}}

.medic-patrol.medic-one {{
    animation-name: medicPatrolOne;
}}

.medic-patrol.medic-two {{
    animation-name: medicPatrolTwo;
}}

@keyframes pulseRing {{
    0% {{ opacity: 0.8; transform: scale(1); }}
    100% {{ opacity: 0; transform: scale(2); }}
}}

@keyframes reticleSpin {{
    from {{ transform: rotate(0deg); }}
    to {{ transform: rotate(360deg); }}
}}

@keyframes suggestionPing {{
    0% {{ opacity: 0.7; transform: scale(1); }}
    100% {{ opacity: 0; transform: scale(2.5); }}
}}

@keyframes medicPatrolOne {{
    0% {{ transform: translate(0px, 0px); }}
    25% {{ transform: translate(12px, -10px); }}
    50% {{ transform: translate(-8px, 9px); }}
    75% {{ transform: translate(15px, 6px); }}
    100% {{ transform: translate(0px, 0px); }}
}}

@keyframes medicPatrolTwo {{
    0% {{ transform: translate(0px, 0px); }}
    25% {{ transform: translate(-13px, 8px); }}
    50% {{ transform: translate(10px, -11px); }}
    75% {{ transform: translate(-6px, 12px); }}
    100% {{ transform: translate(0px, 0px); }}
}}
</style>
"""


@dataclass(frozen=True)
class SuggestionView:
    source: str
    text: str
    confidence: float
    timestamp: datetime | None


class _RankerStateProxy:
    def get_pending_suggestions(self):
        return app_state.get_pending_suggestions()

    def upsert_casualty(self, casualty: Casualty) -> None:
        return None

    def audit(self, source: str, action: str, details: dict) -> None:
        return None


def _ensure_seeded() -> None:
    st.session_state.setdefault("_scenario_state", "bootstrap")
    if st.session_state.get("_scenario_state") in {"simulation", "off", "live_vision"}:
        return
    if not app_state.get_roster():
        seed()
        st.session_state["_scenario_state"] = "baseline"


def _query_value(key: str) -> str | None:
    value = st.query_params.get(key)
    if isinstance(value, list):
        value = value[0] if value else None
    if value in (None, ""):
        return None
    return str(value)


def _sync_selection(valid_ids: set[str], medic_ids: set[str]) -> str | None:
    st.session_state.setdefault("selected_id", None)
    selected_query = _query_value("selected")
    if selected_query == "__clear__":
        st.session_state.selected_id = None
    elif selected_query is not None:
        st.session_state.selected_id = selected_query

    selected_id = st.session_state.selected_id
    if selected_id not in valid_ids | medic_ids:
        st.session_state.selected_id = None
    return st.session_state.selected_id


def _selection_link(selected_id: str) -> str:
    return f"?selected={quote(selected_id, safe='')}"


def _clear_selection_link() -> str:
    return "?selected=__clear__"


def _format_percent(value: float | None) -> int:
    confidence = float(value or 0.0)
    if confidence <= 1:
        confidence *= 100
    return max(0, min(100, int(round(confidence))))


def _format_timestamp(value: datetime | None) -> str:
    if value is None:
        return "UNKNOWN"
    timestamp = value
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone()
    return timestamp.strftime("%H:%M:%S")


def _truncate(value: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _compact_markup(markup: str) -> str:
    return re.sub(r">\s+<", "><", str(markup or "")).strip()


def _pretty_text(value: str) -> str:
    return str(value or "").replace("_", " ").strip().title()


def _triage_fill(category: TriageCategory) -> str:
    style = TRIAGE_MARK_STYLES.get(category, TRIAGE_MARK_STYLES[TriageCategory.UNASSESSED])
    return GRAY if style["fill"] == "none" else str(style["fill"])


def _triage_dot_html(category: TriageCategory) -> str:
    style = TRIAGE_MARK_STYLES.get(category, TRIAGE_MARK_STYLES[TriageCategory.UNASSESSED])
    fill = "transparent" if style["fill"] == "none" else str(style["fill"])
    return (
        f'<span class="triage-dot" style="background:{fill};border:1.5px solid {style["stroke"]};"></span>'
    )


def _distance(point_a: tuple[int, int], point_b: tuple[int, int]) -> float:
    dx = point_a[0] - point_b[0]
    dy = point_a[1] - point_b[1]
    return math.hypot(dx, dy)


def _map_position_seed(casualty_id: str) -> int:
    return int(hashlib.md5(casualty_id.encode("utf-8")).hexdigest()[:8], 16)


def _clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))


def _stable_positions(casualties: list[Casualty]) -> dict[str, tuple[int, int]]:
    positions: dict[str, tuple[int, int]] = {}
    occupied = [(medic["x"], medic["y"]) for medic in MEDICS]
    width = COMPOUND_RIGHT - COMPOUND_LEFT
    height = COMPOUND_BOTTOM - COMPOUND_TOP

    # Neal's current simulation lat/lon values are tightly clustered around the
    # same point, so a literal projection collapses casualties into one blob.
    # We instead derive stable pseudo-spatial positions from casualty_id and
    # bias them toward the compound perimeter for a readable tactical cluster.
    for casualty in sorted(casualties, key=lambda item: item.casualty_id):
        seed_value = _map_position_seed(casualty.casualty_id)
        edge = seed_value % 4

        if edge == 0:
            x = COMPOUND_LEFT + 36 + ((seed_value >> 5) % max(80, width - 72))
            y = COMPOUND_TOP - 28 + ((seed_value >> 13) % 56)
        elif edge == 1:
            x = COMPOUND_RIGHT - 28 + ((seed_value >> 9) % 58)
            y = COMPOUND_TOP + 34 + ((seed_value >> 3) % max(80, height - 68))
        elif edge == 2:
            x = COMPOUND_LEFT + 30 + ((seed_value >> 7) % max(80, width - 60))
            y = COMPOUND_BOTTOM - 24 + ((seed_value >> 15) % 52)
        else:
            x = COMPOUND_LEFT - 34 + ((seed_value >> 11) % 58)
            y = COMPOUND_TOP + 28 + ((seed_value >> 1) % max(80, height - 56))

        x = _clamp(int(x), SAFE_PADDING, MAP_WIDTH - SAFE_PADDING)
        y = _clamp(int(y), SAFE_PADDING, MAP_HEIGHT - SAFE_PADDING)

        for step in range(28):
            candidate = (x, y)
            if all(_distance(candidate, existing) >= 62 for existing in occupied):
                break
            x = _clamp(x + 19 + (step * 5), SAFE_PADDING, MAP_WIDTH - SAFE_PADDING)
            y = _clamp(y - 11 + (step * 7), SAFE_PADDING, MAP_HEIGHT - SAFE_PADDING)

        positions[casualty.casualty_id] = (x, y)
        occupied.append((x, y))

    if positions and not any(_nearest_medic(position)[1] > UNASSIGNED_DISTANCE for position in positions.values()):
        farthest_id = sorted(positions)[-1]
        # Keep one deterministic outlier in the compound's outer ring so the
        # tactical view can surface the red dashed "too far" assignment state.
        positions[farthest_id] = (
            _clamp(COMPOUND_RIGHT + 180, SAFE_PADDING, MAP_WIDTH - SAFE_PADDING),
            _clamp(COMPOUND_TOP - 120, SAFE_PADDING, MAP_HEIGHT - SAFE_PADDING),
        )

    return positions


def _top_wound_label(casualty: Casualty) -> str:
    if not casualty.wounds:
        return "none"
    ranked = sorted(
        casualty.wounds,
        key=lambda wound: (
            {"severe": 3, "moderate": 2, "minor": 1}.get(getattr(wound, "severity", "").lower(), 0),
            float(getattr(wound, "area_cm2", 0.0) or 0.0),
            float(getattr(wound, "ai_confidence", 0.0) or 0.0),
        ),
        reverse=True,
    )
    primary = ranked[0]
    return _pretty_text(getattr(primary, "location", "unknown"))


def _wound_summary(casualty: Casualty) -> str:
    if not casualty.wounds:
        return "No wound structures logged"
    bleeding_count = sum(1 for wound in casualty.wounds if bool(getattr(wound, "active_bleeding", False)))
    top = _top_wound_label(casualty)
    return f"{len(casualty.wounds)} wounds · {bleeding_count} bleeding · top {top}"


def _normalize_timestamp(value: object) -> datetime | None:
    return value if isinstance(value, datetime) else None


def _timestamp_value(value: datetime | None) -> float:
    if value is None:
        return 0.0
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).timestamp()
    return value.timestamp()


def _strip_casualty_prefix(text: str, casualty_id: str) -> str:
    prefix = f"{casualty_id}:"
    cleaned = text.strip()
    if cleaned.startswith(prefix):
        return cleaned[len(prefix) :].strip()
    return cleaned


def _pending_suggestions_map() -> dict[str, list[SuggestionView]]:
    pending_by_casualty: dict[str, list[SuggestionView]] = {}
    for pending in app_state.get_pending_suggestions():
        if not pending.casualty_id:
            continue
        raw = pending.raw
        text = str(getattr(raw, "suggestion", "") or "")
        if not text:
            text = str(raw)
        pending_by_casualty.setdefault(pending.casualty_id, []).append(
            SuggestionView(
                source=str(getattr(raw, "source", pending.source) or pending.source or "unknown"),
                text=text,
                confidence=float(getattr(raw, "confidence", pending.confidence) or pending.confidence or 0.0),
                timestamp=_normalize_timestamp(getattr(raw, "timestamp", pending.created_at) or pending.created_at),
            )
        )
    return pending_by_casualty


def _suggestion_signature(item: SuggestionView) -> tuple[str, str, int, str]:
    timestamp = item.timestamp.isoformat() if item.timestamp else ""
    return (item.source.lower(), item.text.strip(), _format_percent(item.confidence), timestamp)


def _casualty_suggestions(
    casualty: Casualty,
    pending_by_casualty: dict[str, list[SuggestionView]],
    *,
    source: str | None = None,
) -> list[SuggestionView]:
    items: list[SuggestionView] = []
    for suggestion in casualty.ai_suggestions_log:
        items.append(
            SuggestionView(
                source=str(getattr(suggestion, "source", "unknown") or "unknown"),
                text=str(getattr(suggestion, "suggestion", "") or ""),
                confidence=float(getattr(suggestion, "confidence", 0.0) or 0.0),
                timestamp=_normalize_timestamp(getattr(suggestion, "timestamp", None)),
            )
        )
    items.extend(pending_by_casualty.get(casualty.casualty_id, []))

    deduped: dict[tuple[str, str, int], SuggestionView] = {}
    for item in items:
        if not item.text.strip():
            continue
        if source is not None and item.source.lower() != source.lower():
            continue
        key = (item.source.lower(), item.text.strip(), _format_percent(item.confidence))
        previous = deduped.get(key)
        if previous is None or (item.timestamp or datetime.min) > (previous.timestamp or datetime.min):
            deduped[key] = item
    return sorted(
        deduped.values(),
        key=lambda item: (_timestamp_value(item.timestamp), item.confidence, item.text),
        reverse=True,
    )


def _top_suggestion(casualty: Casualty, pending_by_casualty: dict[str, list[SuggestionView]]) -> SuggestionView | None:
    suggestions = _casualty_suggestions(casualty, pending_by_casualty)
    if not suggestions:
        return None
    return max(
        suggestions,
        key=lambda item: (
            item.confidence,
            _timestamp_value(item.timestamp),
            0 if item.source.lower() == "fusion" else 1,
        ),
    )


def _latest_suggestion_time(casualty: Casualty, pending_by_casualty: dict[str, list[SuggestionView]]) -> datetime | None:
    suggestions = _casualty_suggestions(casualty, pending_by_casualty)
    if not suggestions:
        return None
    latest = max(suggestions, key=lambda item: _timestamp_value(item.timestamp), default=None)
    return latest.timestamp if latest else None


def _simulation_asset(casualty_id: str, simulation_assets: dict[str, dict], kind: str) -> Path | None:
    asset_value = simulation_assets.get(casualty_id, {}).get(kind)
    if asset_value is None:
        return None
    return resolve_sim_asset(str(asset_value))


def _diagnosis_text(casualty_id: str, simulation_assets: dict[str, dict]) -> str:
    return str(simulation_assets.get(casualty_id, {}).get("diagnosis", "") or "").strip()


def _reasoning_text(casualty_id: str, simulation_assets: dict[str, dict]) -> str:
    reasoning = simulation_assets.get(casualty_id, {}).get("reasoning")
    if reasoning is None:
        return ""
    if isinstance(reasoning, str):
        return reasoning.strip()
    if isinstance(reasoning, (list, tuple, set)):
        parts = [str(part).strip() for part in reasoning if str(part).strip()]
        return " ".join(parts)
    return str(reasoning).strip()


def _audio_asset(casualty_id: str, simulation_assets: dict[str, dict]) -> Path | None:
    audio_path = _simulation_asset(casualty_id, simulation_assets, "audio")
    if audio_path is None:
        return None
    return audio_path if audio_path.suffix.lower() in AUDIO_EXTENSIONS else None


def _queue_patient_label(casualty_id: str) -> str:
    raw_value = str(casualty_id).strip()
    if match := re.fullmatch(r"A0*(\d+)", raw_value, re.IGNORECASE):
        return f"Patient {int(match.group(1)):02d}"
    if match := re.fullmatch(r"Patient[\s_-]*0*(\d+)", raw_value, re.IGNORECASE):
        return f"Patient {int(match.group(1)):02d}"
    return raw_value


def _queue_track_label(casualty_id: str) -> str | None:
    raw_value = str(casualty_id).strip()
    if match := re.fullmatch(r"A0*(\d+)", raw_value, re.IGNORECASE):
        return f"Track A{int(match.group(1))}"
    return None


def _demo_elapsed_seconds() -> float | None:
    scenario_state = str(st.session_state.get("_scenario_state", "") or "")
    if scenario_state not in {"scripted", "live_vision"}:
        return None

    player = st.session_state.get("demo_player")
    status = getattr(player, "status", None)
    if not isinstance(status, dict):
        return 0.0
    return float(status.get("t", 0.0) or 0.0)


def _medic_pov_frame(medic_id: str):
    elapsed = _demo_elapsed_seconds()
    if elapsed is None:
        return None

    clip_path = get_medic_pov_clip(medic_id)
    if clip_path is None:
        return None
    return sample_curated_frame(clip_path, elapsed_seconds=elapsed)


def _top_concern(casualty: Casualty, pending_by_casualty: dict[str, list[SuggestionView]], simulation_assets: dict[str, dict]) -> str:
    top_suggestion = _top_suggestion(casualty, pending_by_casualty)
    if top_suggestion is not None:
        return _truncate(_strip_casualty_prefix(top_suggestion.text, casualty.casualty_id), 84)
    if casualty.wounds:
        return _truncate(_wound_summary(casualty), 84)
    diagnosis = _diagnosis_text(casualty.casualty_id, simulation_assets)
    if diagnosis:
        return _truncate(diagnosis, 84)
    return "Awaiting assessment"


def _top_confidence(casualty: Casualty, pending_by_casualty: dict[str, list[SuggestionView]]) -> int:
    top_suggestion = _top_suggestion(casualty, pending_by_casualty)
    if top_suggestion is None:
        return 0
    return _format_percent(top_suggestion.confidence)


def _tooltip_position(x: int, y: int) -> tuple[int, int]:
    width = 232
    height = 110
    offset = 18
    left = x + offset if x <= MAP_WIDTH - width - 28 else x - width - offset
    top = y - height - offset if y >= MAP_HEIGHT - height - 28 else y + offset
    left = max(12, min(MAP_WIDTH - width - 12, left))
    top = max(12, min(MAP_HEIGHT - height - 12, top))
    return (left, top)


def _tooltip_html(
    casualty: Casualty,
    x: int,
    y: int,
    pending_by_casualty: dict[str, list[SuggestionView]],
    simulation_assets: dict[str, dict],
) -> str:
    tooltip_x, tooltip_y = _tooltip_position(x, y)
    concern = _wound_summary(casualty) if casualty.wounds else _diagnosis_text(casualty.casualty_id, simulation_assets)
    concern = _truncate(concern or "Awaiting assessment", 80)
    confidence = _top_confidence(casualty, pending_by_casualty)
    audio_path = _simulation_asset(casualty.casualty_id, simulation_assets, "audio")
    triage = triage_label(casualty.triage_category)
    tooltip_title = html.escape(casualty.casualty_id)
    audio_badge = '<div class="tooltip-audio">🎧 CLIP AVAILABLE</div>' if audio_path else ""
    title_text = html.escape(f"{casualty.casualty_id} · {triage} · {concern}")
    return f"""
    <foreignObject class="tooltip-fo" x="{tooltip_x}" y="{tooltip_y}" width="232" height="110">
        <div xmlns="http://www.w3.org/1999/xhtml" class="tooltip-card">
            <div class="tooltip-title">{tooltip_title}</div>
            <div class="tooltip-triage">{_triage_dot_html(casualty.triage_category)}{html.escape(triage)}</div>
            <div class="tooltip-copy">{html.escape(concern)}</div>
            <div class="tooltip-meta">AI · {confidence}%</div>
            {audio_badge}
        </div>
    </foreignObject>
    <title>{title_text}</title>
    """


def _corner_markers() -> str:
    markers = []
    for x, y in ((95, 95), (905, 95), (95, 505), (905, 505)):
        markers.append(
            f"""
            <line x1="{x - 8}" y1="{y}" x2="{x + 8}" y2="{y}" stroke="{GOLD}" stroke-width="1.5" />
            <line x1="{x}" y1="{y - 8}" x2="{x}" y2="{y + 8}" stroke="{GOLD}" stroke-width="1.5" />
            """
        )
    return "".join(markers)


def _grid_lines(step: int, stroke: str, stroke_width: float) -> str:
    verticals = [
        f'<line x1="{x}" y1="0" x2="{x}" y2="{MAP_HEIGHT}" stroke="{stroke}" stroke-width="{stroke_width}" />'
        for x in range(0, MAP_WIDTH + 1, step)
    ]
    horizontals = [
        f'<line x1="0" y1="{y}" x2="{MAP_WIDTH}" y2="{y}" stroke="{stroke}" stroke-width="{stroke_width}" />'
        for y in range(0, MAP_HEIGHT + 1, step)
    ]
    return "".join(verticals + horizontals)


def _terrain_pattern() -> str:
    return f"""
    <defs>
        <pattern id="terrainPattern" x="0" y="0" width="180" height="120" patternUnits="userSpaceOnUse">
            <path d="M0 20 C35 0 90 0 140 18 S210 42 180 62" fill="none" stroke="#D8D4C8" stroke-width="1" opacity="0.4" />
            <path d="M-12 60 C25 42 74 42 122 60 S195 92 180 104" fill="none" stroke="#D8D4C8" stroke-width="1" opacity="0.4" />
            <path d="M0 98 C44 78 96 82 148 100 S212 132 176 142" fill="none" stroke="#D8D4C8" stroke-width="1" opacity="0.4" />
        </pattern>
    </defs>
    """


def _nearest_medic(position: tuple[int, int]) -> tuple[dict[str, object], float]:
    return min(
        ((medic, _distance(position, (int(medic["x"]), int(medic["y"])))) for medic in MEDICS),
        key=lambda item: item[1],
    )


def _category_from_ranker(priority_value: object, casualty: Casualty) -> TriageCategory:
    if isinstance(priority_value, TriageCategory):
        return priority_value
    if isinstance(priority_value, str):
        return PRIORITY_VALUE_TO_CATEGORY.get(priority_value.lower(), casualty.triage_category)
    return casualty.triage_category


def _fallback_ranking(
    casualties: list[Casualty],
    pending_by_casualty: dict[str, list[SuggestionView]],
    simulation_assets: dict[str, dict],
) -> list[dict]:
    rows = []
    for casualty in casualties:
        top_suggestion = _top_suggestion(casualty, pending_by_casualty)
        rows.append(
            {
                "casualty_id": casualty.casualty_id,
                "category": casualty.triage_category,
                "confidence": top_suggestion.confidence if top_suggestion else 0.0,
                "top_concern": _top_concern(casualty, pending_by_casualty, simulation_assets),
            }
        )
    rows.sort(
        key=lambda row: (
            LOCAL_PRIORITY_RANK.get(row["category"], 99),
            -float(row["confidence"] or 0.0),
            str(row["casualty_id"]),
        )
    )
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def _ranked_roster(
    casualties: list[Casualty],
    pending_by_casualty: dict[str, list[SuggestionView]],
    simulation_assets: dict[str, dict],
) -> list[dict]:
    casualty_map = {casualty.casualty_id: casualty for casualty in casualties}
    engine = start_triage_engine()
    original_ranker_state = scenario_ranker_module.app_state
    original_analyze = engine.analyze_casualty

    def _analyze_without_side_effects(self, casualty: Casualty):
        try:
            evidence = self.gather_evidence(casualty)
            scores = self.calculate_triage_scores(evidence)
            rule_priority = self.determine_priority(scores)
            llm_result = self.llm_analyzer.enhance_triage_reasoning(
                evidence, scores, rule_priority.value
            )
            return AISuggestion(
                timestamp=datetime.now(),
                source="triage_engine_llm",
                suggestion=f"Suggested triage: {llm_result['priority']} priority - {'; '.join(llm_result['reasoning'][:2])}",
                confidence=llm_result["confidence"],
            )
        except Exception:
            return None

    engine.analyze_casualty = MethodType(_analyze_without_side_effects, engine)
    scenario_ranker_module.app_state = _RankerStateProxy()
    try:
        ranked = rank_roster(engine, casualties)
    except Exception:
        return _fallback_ranking(casualties, pending_by_casualty, simulation_assets)
    finally:
        scenario_ranker_module.app_state = original_ranker_state
        engine.analyze_casualty = original_analyze

    rows = []
    for index, item in enumerate(ranked, start=1):
        casualty = casualty_map.get(str(item.get("casualty_id")))
        if casualty is None:
            continue
        concern = str(item.get("reasoning", "") or "").strip()
        concern = _strip_casualty_prefix(concern, casualty.casualty_id)
        if not concern:
            concern = _top_concern(casualty, pending_by_casualty, simulation_assets)
        rows.append(
            {
                "rank": index,
                "casualty_id": casualty.casualty_id,
                "category": _category_from_ranker(item.get("priority"), casualty),
                "confidence": float(item.get("confidence", 0.0) or 0.0),
                "top_concern": _truncate(concern, 76),
            }
        )

    if not rows:
        return _fallback_ranking(casualties, pending_by_casualty, simulation_assets)
    return rows


def _map_svg(
    casualties: list[Casualty],
    selected_id: str | None,
    ranked_rows: list[dict],
    pending_by_casualty: dict[str, list[SuggestionView]],
    simulation_assets: dict[str, dict],
) -> str:
    positions = _stable_positions(casualties)
    top_priority_id = ranked_rows[0]["casualty_id"] if ranked_rows else None
    counts = {
        TriageCategory.IMMEDIATE: 0,
        TriageCategory.DELAYED: 0,
        TriageCategory.MINIMAL: 0,
    }
    for casualty in casualties:
        counts[casualty.triage_category] = counts.get(casualty.triage_category, 0) + 1

    timestamp = datetime.now().astimezone().strftime("%H:%M:%S")
    status_text = (
        f"{len(casualties)} CASUALTIES · "
        f"{counts.get(TriageCategory.IMMEDIATE, 0)} IMMEDIATE · "
        f"{counts.get(TriageCategory.DELAYED, 0)} DELAYED · "
        f"{counts.get(TriageCategory.MINIMAL, 0)} MINIMAL · "
        f"{len(MEDICS)} MEDICS"
    )

    assignment_lines: list[str] = []
    casualty_groups: list[str] = []

    for casualty in casualties:
        x, y = positions[casualty.casualty_id]
        medic, distance = _nearest_medic((x, y))
        line_color = GOLD
        line_opacity = "0.3"
        dasharray = ""
        if distance > UNASSIGNED_DISTANCE:
            line_color = RED
            line_opacity = "0.6"
            dasharray = ' stroke-dasharray="4 4"'
        assignment_lines.append(
            f'<line x1="{int(medic["x"])}" y1="{int(medic["y"])}" x2="{x}" y2="{y}" '
            f'stroke="{line_color}" stroke-width="1" opacity="{line_opacity}"{dasharray} />'
        )

        label_y = y - 20
        category_style = TRIAGE_MARK_STYLES.get(casualty.triage_category, TRIAGE_MARK_STYLES[TriageCategory.UNASSESSED])
        pulse_ring = ""
        selected_ring = ""
        ping_ring = ""
        priority_reticle = ""
        if casualty.triage_category == TriageCategory.UNASSESSED:
            marker = (
                f'<circle cx="{x}" cy="{y}" r="12" fill="none" stroke="#FAFAF6" stroke-width="4" />'
                f'<circle cx="{x}" cy="{y}" r="12" fill="none" stroke="{category_style["stroke"]}" stroke-width="2" />'
            )
        else:
            marker = (
                f'<circle cx="{x}" cy="{y}" r="12" fill="{category_style["fill"]}" stroke="#FAFAF6" stroke-width="2" />'
            )
        if casualty.triage_category == TriageCategory.IMMEDIATE:
            pulse_ring = f'<circle class="pulse-ring" cx="{x}" cy="{y}" r="12" fill="none" stroke="{RED}" stroke-width="1.5" />'

        latest_suggestion = _latest_suggestion_time(casualty, pending_by_casualty)
        if latest_suggestion is not None and (datetime.now(latest_suggestion.tzinfo) - latest_suggestion).total_seconds() <= 1.1:
            ping_ring = (
                f'<circle class="ping-ring" cx="{x}" cy="{y}" r="12" fill="none" stroke="{GOLD}" stroke-width="2" />'
            )

        if casualty.casualty_id == top_priority_id:
            priority_reticle = f"""
            <g class="reticle-rotate priority-reticle" style="transform-origin: {x}px {y}px;">
                <circle cx="{x}" cy="{y}" r="22" fill="none" stroke="{GOLD}" stroke-width="1.2" stroke-dasharray="6 8" />
                <line x1="{x}" y1="{y - 28}" x2="{x}" y2="{y - 22}" stroke="{GOLD}" stroke-width="1.1" />
                <line x1="{x + 22}" y1="{y}" x2="{x + 28}" y2="{y}" stroke="{GOLD}" stroke-width="1.1" />
                <line x1="{x}" y1="{y + 22}" x2="{x}" y2="{y + 28}" stroke="{GOLD}" stroke-width="1.1" />
                <line x1="{x - 28}" y1="{y}" x2="{x - 22}" y2="{y}" stroke="{GOLD}" stroke-width="1.1" />
            </g>
            """

        if casualty.casualty_id == selected_id:
            selected_ring = f"""
            <circle cx="{x}" cy="{y}" r="18" fill="none" stroke="{GOLD}" stroke-width="2" />
            <g class="reticle-rotate" style="transform-origin: {x}px {y}px;">
                <circle class="selected-reticle" cx="{x}" cy="{y}" r="24" fill="none" stroke="{GOLD}" stroke-width="1.3" stroke-dasharray="5 7" />
                <line x1="{x}" y1="{y - 30}" x2="{x}" y2="{y - 24}" stroke="{GOLD}" stroke-width="1.2" />
                <line x1="{x + 24}" y1="{y}" x2="{x + 30}" y2="{y}" stroke="{GOLD}" stroke-width="1.2" />
                <line x1="{x}" y1="{y + 24}" x2="{x}" y2="{y + 30}" stroke="{GOLD}" stroke-width="1.2" />
                <line x1="{x - 30}" y1="{y}" x2="{x - 24}" y2="{y}" stroke="{GOLD}" stroke-width="1.2" />
            </g>
            """

        casualty_groups.append(
            f"""
            <g class="map-contact casualty-group">
                <a class="map-link" href="{_selection_link(casualty.casualty_id)}" target="_self">
                    <circle class="hover-glow" cx="{x}" cy="{y}" r="20" fill="{GOLD}" />
                    {priority_reticle}
                    {pulse_ring}
                    {ping_ring}
                    {selected_ring}
                    {marker}
                    <text class="map-label" x="{x}" y="{label_y}" text-anchor="middle">{html.escape(casualty.casualty_id)} · {html.escape(triage_label(casualty.triage_category))}</text>
                </a>
                {_tooltip_html(casualty, x, y, pending_by_casualty, simulation_assets)}
            </g>
            """
        )

    medic_groups = []
    for medic in MEDICS:
        selected_ring = ""
        if selected_id == medic["id"]:
            selected_ring = (
                f'<circle cx="{medic["x"]}" cy="{medic["y"]}" r="20" fill="none" stroke="{GOLD}" stroke-width="1.8" />'
            )
        medic_groups.append(
            f"""
            <g class="map-contact medic-group medic-patrol {medic["css"]}">
                <a class="map-link" href="{_selection_link(str(medic["id"]))}" target="_self">
                    <circle cx="{medic["x"]}" cy="{medic["y"]}" r="{MEDIC_COVERAGE_RADIUS}" fill="none" stroke="{GOLD}" stroke-width="1.2" opacity="0.15" stroke-dasharray="2 4" />
                    <circle class="hover-glow" cx="{medic["x"]}" cy="{medic["y"]}" r="22" fill="{GOLD}" />
                    {selected_ring}
                    <rect x="{int(medic["x"]) - 8}" y="{int(medic["y"]) - 8}" width="16" height="16" rx="1.5" fill="{GOLD}" transform="rotate(45 {medic["x"]} {medic["y"]})" />
                    <text class="medic-label" x="{medic["x"]}" y="{int(medic["y"]) + 28}" text-anchor="middle">{html.escape(str(medic["label"]))}</text>
                </a>
            </g>
            """
        )

    svg_markup = f"""
    <div class="map-shell">
    <svg width="100%" viewBox="0 0 {MAP_WIDTH} {MAP_HEIGHT}" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="AEGIS tactical map">
        {_terrain_pattern()}
        <rect x="0" y="0" width="{MAP_WIDTH}" height="{MAP_HEIGHT}" fill="{BACKGROUND}" />
        <rect x="0" y="0" width="{MAP_WIDTH}" height="{MAP_HEIGHT}" fill="url(#terrainPattern)" />
        <g class="map-grid">
            {_grid_lines(50, "#E8E4D8", 1)}
            {_grid_lines(250, "#D8D4C8", 1.5)}
        </g>
        <rect x="{COMPOUND_LEFT}" y="{COMPOUND_TOP}" width="{COMPOUND_RIGHT - COMPOUND_LEFT}" height="{COMPOUND_BOTTOM - COMPOUND_TOP}" fill="none" stroke="{GOLD}" stroke-width="1.5" stroke-dasharray="8 4" opacity="0.35" />
        <text class="map-grid-label" x="{COMPOUND_LEFT + 14}" y="{COMPOUND_TOP + 18}">STRUCTURE · PARTIAL COLLAPSE</text>
        <text class="quadrant-label" x="250" y="150" text-anchor="middle">A1</text>
        <text class="quadrant-label" x="750" y="150" text-anchor="middle">A2</text>
        <text class="quadrant-label" x="250" y="450" text-anchor="middle">B1</text>
        <text class="quadrant-label" x="750" y="450" text-anchor="middle">B2</text>
        <g class="map-corners">{_corner_markers()}</g>
        <text class="map-grid-label" x="24" y="26">GRID 38TKL 042 119 · STYLIZED OVERHEAD</text>
        <text class="map-status" x="976" y="26" text-anchor="end">{html.escape(status_text)}</text>
        <g class="assignment-lines">{''.join(assignment_lines)}</g>
        <g class="medic-layer">{''.join(medic_groups)}</g>
        <g class="map-casualties">{''.join(casualty_groups)}</g>
        <text class="map-footer" x="24" y="578">{timestamp}</text>
        <text class="map-footer" x="976" y="578" text-anchor="end" fill="{GOLD}">AEGIS ◆</text>
    </svg>
    </div>
    """
    return re.sub(r">\s+<", "><", svg_markup).strip()


def _queue_html(ranked_rows: list[dict], selected_id: str | None) -> str:
    rows = []
    for row in ranked_rows:
        category = row["category"]
        style = TRIAGE_MARK_STYLES.get(category, TRIAGE_MARK_STYLES[TriageCategory.UNASSESSED])
        fill = "transparent" if style["fill"] == "none" else str(style["fill"])
        classes = ["queue-row"]
        if row["rank"] == 1:
            classes.append("top")
        if row["casualty_id"] == selected_id:
            classes.append("selected")
        track_label = _queue_track_label(str(row["casualty_id"]))
        track_markup = f'<div class="queue-track">{html.escape(track_label)}</div>' if track_label else ""
        rows.append(
            f"""
            <div class="{' '.join(classes)}">
                <div class="queue-leading">
                    <div class="queue-rank">{int(row["rank"]):02d}</div>
                    <div class="queue-dot" style="background:{fill};border:1.5px solid {style["stroke"]};"></div>
                </div>
                <div class="queue-main">
                    <div class="queue-name">{html.escape(_queue_patient_label(str(row["casualty_id"])))}</div>
                    {track_markup}
                    <div class="queue-summary">{html.escape(str(row["top_concern"]))}</div>
                </div>
                <a class="queue-select" href="{_selection_link(str(row["casualty_id"]))}" target="_self">SELECT</a>
            </div>
            """
        )

    if not rows:
        rows.append('<div class="detail-copy">No casualties in the live roster.</div>')

    return _compact_markup(
        f"""
        <div>
            <div class="queue-title">ACTION QUEUE</div>
            <div class="queue-subtitle" style="margin-top:0.35rem;margin-bottom:0.8rem;">WHO NEEDS ATTENTION FIRST</div>
            <div class="queue-list">{''.join(rows)}</div>
        </div>
        """
    )


def _empty_detail_panel() -> None:
    st.markdown(
        """
        <div class="detail-title small">Click a casualty on the map</div>
        <div class="detail-copy" style="margin-top:0.7rem;">
            Use the tactical plot or the queue to inspect one patient or a medic zone.
        </div>
        <div class="empty-panel" style="margin-top:1rem;">Selection idle</div>
        """,
        unsafe_allow_html=True,
    )


def _vision_section_html(casualty: Casualty, vision_rows: list[SuggestionView]) -> str:
    rows = []
    for item in vision_rows:
        rows.append(
            f"""
            <div class="vision-row">
                <div style="flex:1 1 auto;min-width:0;">{html.escape(_strip_casualty_prefix(item.text, casualty.casualty_id))}</div>
                <div class="vision-meta">AI · {_format_percent(item.confidence)}%</div>
            </div>
            """
        )

    if casualty.wounds:
        rows.append(f'<div class="info-row"><div>{html.escape(_wound_summary(casualty))}</div></div>')

    if not rows:
        rows.append('<div class="detail-copy">No vision data yet</div>')
    return _compact_markup("".join(rows))


def _interventions_html(casualty: Casualty) -> str:
    if not casualty.interventions:
        return '<div class="detail-copy">None logged</div>'
    rows = []
    for intervention in casualty.interventions:
        rows.append(
            f"""
            <div class="intervention-row">
                <div>{html.escape(_pretty_text(getattr(intervention, "type", "unknown")))} · {html.escape(_pretty_text(getattr(intervention, "location", "unknown")))}</div>
                <div class="intervention-meta">{_format_timestamp(getattr(intervention, "timestamp", None))}</div>
            </div>
            """
        )
    return _compact_markup("".join(rows))


def _render_medic_panel(
    selected_id: str,
    casualties: list[Casualty],
    positions: dict[str, tuple[int, int]],
    ranked_rows: list[dict],
    pending_by_casualty: dict[str, list[SuggestionView]],
    simulation_assets: dict[str, dict],
) -> None:
    medic = next((item for item in MEDICS if item["id"] == selected_id), MEDICS[0])
    st.markdown(
        f"""
        <div class="detail-kicker">{html.escape(str(medic["label"]))}</div>
        <div class="detail-title small">Medic POV</div>
        """,
        unsafe_allow_html=True,
    )

    frame = _medic_pov_frame(selected_id)
    if frame is not None:
        st.image(frame, channels="BGR", width="stretch")
    else:
        st.markdown(
            """
            <div class="medic-feed-empty">
                <div class="medic-feed-empty-inner">
                    <div class="medic-feed-glyph">AEGIS ◆</div>
                    <div class="medic-feed-kicker">NO LIVE FEED</div>
                    <div class="medic-feed-copy">Start a scripted demo from the dashboard to see this medic&apos;s POV.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="detail-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="detail-kicker">ZONE ROSTER</div>', unsafe_allow_html=True)

    zone_rows = []
    medic_position = (int(medic["x"]), int(medic["y"]))
    ranked_lookup = {row["casualty_id"]: row for row in ranked_rows}
    zone_ranked_rows = []

    for casualty in casualties:
        position = positions[casualty.casualty_id]
        if _distance(position, medic_position) <= MEDIC_ZONE_RADIUS:
            zone_ranked_rows.append(ranked_lookup.get(casualty.casualty_id, {"rank": 999, "casualty_id": casualty.casualty_id}))
            concern = _top_concern(casualty, pending_by_casualty, simulation_assets)
            zone_rows.append(
                f"""
                <div class="zone-row">
                    {_triage_dot_html(casualty.triage_category)}
                    <div style="flex:1 1 auto;min-width:0;">
                        <div class="queue-id" style="font-size:0.95rem;">{html.escape(casualty.casualty_id)}</div>
                        <div class="queue-concern">{html.escape(concern)}</div>
                    </div>
                    <a class="zone-select" href="{_selection_link(casualty.casualty_id)}" target="_self">SELECT</a>
                </div>
                """
            )

    if zone_rows:
        st.markdown(_compact_markup("".join(zone_rows)), unsafe_allow_html=True)
    else:
        st.markdown('<div class="detail-copy">No casualties currently inside this medic\'s zone.</div>', unsafe_allow_html=True)

    zone_ranked_rows = [row for row in zone_ranked_rows if row]
    zone_ranked_rows.sort(key=lambda row: int(row.get("rank", 999)))
    current_patient = zone_ranked_rows[0]["casualty_id"] if zone_ranked_rows else "None"

    st.markdown('<div class="detail-divider"></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="mono-line">Current patient · {html.escape(str(current_patient))}</div>',
        unsafe_allow_html=True,
    )


def _render_casualty_panel(
    casualty: Casualty,
    rank_lookup: dict[str, int],
    pending_by_casualty: dict[str, list[SuggestionView]],
    simulation_assets: dict[str, dict],
) -> None:
    rank_display = rank_lookup.get(casualty.casualty_id)
    vision_rows = _casualty_suggestions(casualty, pending_by_casualty, source="vision")
    audio_rows = _casualty_suggestions(casualty, pending_by_casualty, source="audio")
    audio_path = _audio_asset(casualty.casualty_id, simulation_assets)
    image_path = _simulation_asset(casualty.casualty_id, simulation_assets, "image")
    diagnosis = _diagnosis_text(casualty.casualty_id, simulation_assets)
    reasoning = _reasoning_text(casualty.casualty_id, simulation_assets)

    st.markdown(
        f"""
        <div class="detail-title">Casualty {html.escape(casualty.casualty_id)}</div>
        <div class="identity-line">{_triage_dot_html(casualty.triage_category)}{html.escape(triage_label(casualty.triage_category))}</div>
        <div class="mono-line">LAST SEEN · {_format_timestamp(casualty.last_seen)}</div>
        <div class="detail-rank">Priority Rank · #{rank_display if rank_display is not None else "-"}</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="detail-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="detail-kicker">VISION</div>', unsafe_allow_html=True)
    if image_path is not None and image_path.suffix.lower() in IMAGE_EXTENSIONS:
        st.image(str(image_path), width="stretch")
    st.markdown(_vision_section_html(casualty, vision_rows), unsafe_allow_html=True)

    st.markdown('<div class="detail-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="detail-kicker">AUDIO</div>', unsafe_allow_html=True)
    if audio_path is not None:
        st.audio(str(audio_path), width="stretch")
        st.markdown(f'<div class="clip-meta">CLIP · {html.escape(audio_path.name)}</div>', unsafe_allow_html=True)
        if audio_rows:
            top_audio = audio_rows[0]
            st.markdown(
                f"""
                <div class="info-row">
                    <div>{html.escape(_strip_casualty_prefix(top_audio.text, casualty.casualty_id))}</div>
                    <div class="info-meta">AI · {_format_percent(top_audio.confidence)}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            """
            <div class="audio-empty">
                <div class="audio-empty-title">No Verified Audio Clip</div>
                <div class="audio-empty-copy">No repo-backed casualty audio is attached to this record yet.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="detail-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="detail-kicker">DIAGNOSIS</div>', unsafe_allow_html=True)
    if diagnosis:
        st.markdown(f'<div class="italic-diagnosis">{html.escape(diagnosis)}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="detail-copy">No simulation diagnosis attached.</div>', unsafe_allow_html=True)
    if reasoning:
        st.markdown('<div class="detail-kicker" style="margin-top:0.9rem;">TRIAGE RATIONALE</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="rationale-copy">{html.escape(reasoning)}</div>', unsafe_allow_html=True)

    st.markdown('<div class="detail-kicker" style="margin-top:1rem;">INTERVENTIONS</div>', unsafe_allow_html=True)
    st.markdown(_interventions_html(casualty), unsafe_allow_html=True)

    live_color = TEXT_PRIMARY if casualty.triage_category == TriageCategory.DECEASED else GREEN
    live_label = "DECEASED" if casualty.triage_category == TriageCategory.DECEASED else "ALIVE"
    march_total = sum(1 for value in casualty.march_checklist.values() if bool(value))
    st.markdown(
        f"""
        <div class="status-bar">
            <div class="status-pill"><span class="triage-dot" style="background:{live_color};border:1px solid {live_color};"></span>{html.escape(live_label)}</div>
            <div class="march-meta">MARCH · {march_total}/5</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if casualty.medic_notes:
        st.markdown(f'<div class="note-copy">{html.escape(casualty.medic_notes)}</div>', unsafe_allow_html=True)


def _render_detail_panel(
    selected_id: str | None,
    casualties: list[Casualty],
    ranked_rows: list[dict],
    pending_by_casualty: dict[str, list[SuggestionView]],
    simulation_assets: dict[str, dict],
) -> None:
    positions = _stable_positions(casualties)
    casualty_map = {casualty.casualty_id: casualty for casualty in casualties}
    rank_lookup = {row["casualty_id"]: int(row["rank"]) for row in ranked_rows}

    with st.container(border=True):
        if not selected_id:
            _empty_detail_panel()
            return
        if selected_id in {medic["id"] for medic in MEDICS}:
            _render_medic_panel(selected_id, casualties, positions, ranked_rows, pending_by_casualty, simulation_assets)
            return
        casualty = casualty_map.get(selected_id)
        if casualty is None:
            _empty_detail_panel()
            return
        _render_casualty_panel(casualty, rank_lookup, pending_by_casualty, simulation_assets)


st.set_page_config(page_title="AEGIS Tactical Map", layout="wide", initial_sidebar_state="expanded")
st.markdown(STYLE_BLOCK, unsafe_allow_html=True)
_ensure_seeded()
render_sidebar_toggle_bridge()

with st.sidebar:
    controls()


@st.fragment(run_every=0.5)
def render_tactical_map() -> None:
    casualties = app_state.get_roster()
    pending_by_casualty = _pending_suggestions_map()
    simulation_assets = get_simulation_assets()
    medic_ids = {medic["id"] for medic in MEDICS}
    selected_id = _sync_selection({casualty.casualty_id for casualty in casualties}, medic_ids)
    ranked_rows = _ranked_roster(casualties, pending_by_casualty, simulation_assets)

    map_col, detail_col, queue_col = st.columns([8.8, 4.2, 4.0], gap="small")

    with map_col:
        with st.container(border=True):
            reset_link = ""
            if selected_id is not None:
                reset_link = f'<a class="map-reset-link" href="{_clear_selection_link()}" target="_self">Reset Focus</a>'
            st.markdown(
                _compact_markup(
                    f"""
                    <div class="map-toolbar">
                        <div>
                            <div class="detail-kicker" style="margin-bottom:0.25rem;">TACTICAL PLOT</div>
                            <div class="map-toolbar-copy">Field overview with medic coverage, assignment lines, and triage hotspots.</div>
                        </div>
                        {reset_link}
                    </div>
                    <div class="map-card">{_map_svg(casualties, selected_id, ranked_rows, pending_by_casualty, simulation_assets)}</div>
                    """
                ),
                unsafe_allow_html=True,
            )

    with detail_col:
        _render_detail_panel(selected_id, casualties, ranked_rows, pending_by_casualty, simulation_assets)

    with queue_col:
        with st.container(border=True):
            st.markdown(_queue_html(ranked_rows, selected_id), unsafe_allow_html=True)


render_tactical_map()
