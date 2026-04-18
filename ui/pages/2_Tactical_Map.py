from __future__ import annotations

from datetime import datetime
import hashlib
import html
from pathlib import Path
import re
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from schema import Casualty, TriageCategory
from shared.state import app_state
from scripts.seed_fake_data import seed
from ui.components.controls import controls
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
MEDIC_X = 500
MEDIC_Y = 300
SAFE_PADDING = 36
VISION_SOURCE = "#3B5F7C"

TRIAGE_MARK_STYLES = {
    TriageCategory.IMMEDIATE: {"fill": RED, "stroke": "#FAFAF6"},
    TriageCategory.DELAYED: {"fill": AMBER, "stroke": "#FAFAF6"},
    TriageCategory.MINIMAL: {"fill": GREEN, "stroke": "#FAFAF6"},
    TriageCategory.EXPECTANT: {"fill": GRAY, "stroke": "#FAFAF6"},
    TriageCategory.DECEASED: {"fill": TEXT_PRIMARY, "stroke": "#FAFAF6"},
    TriageCategory.UNASSESSED: {"fill": "none", "stroke": GRAY},
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
    --vision: {VISION_SOURCE};
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
    height: 0;
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
    max-width: 1440px;
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

.tactical-layout {{
    display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(320px, 1fr);
    gap: 1rem;
    align-items: start;
}}

.tactical-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    box-shadow: var(--shadow);
}}

.map-shell {{
    padding: 0.75rem;
}}

.map-shell svg {{
    width: 100%;
    height: auto;
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

.medic-group:hover .medic-diamond {{
    fill: #c8951b;
}}

.medic-group:hover .medic-label {{
    text-decoration: underline;
    text-underline-offset: 2px;
}}

.hover-glow {{
    opacity: 0;
    transition: opacity 150ms ease;
    pointer-events: none;
}}

.map-contact:hover .hover-glow {{
    opacity: 0.15;
}}

.pulse-ring {{
    transform-origin: center;
    transform-box: fill-box;
    animation: pulseRing 1.2s ease-out infinite;
    opacity: 0.8;
    pointer-events: none;
}}

.reticle-rotate {{
    animation: reticleSpin 9s linear infinite;
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
    width: 198px;
    min-height: 64px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}}

.tooltip-title {{
    font-family: var(--font-serif);
    font-size: 14px;
    color: var(--text-primary);
    line-height: 1.1;
}}

.tooltip-copy {{
    font-family: var(--font-sans);
    font-size: 11px;
    color: var(--text-muted);
    line-height: 1.35;
    margin-top: 6px;
}}

.tooltip-meta {{
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-primary);
    line-height: 1.2;
    text-align: right;
    margin-top: 6px;
}}

.detail-shell {{
    padding: 1.25rem 1.2rem;
}}

.detail-section {{
    padding: 1.05rem 0 0.95rem;
    border-top: 1px solid var(--divider);
}}

.detail-section:first-child {{
    padding-top: 0;
    border-top: 0;
}}

.section-kicker {{
    color: var(--text-muted);
    font-size: 0.72rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 0.7rem;
}}

.detail-title {{
    font-family: var(--font-serif);
    font-size: 2rem;
    line-height: 1;
    margin: 0;
    color: var(--text-primary);
}}

.detail-title.small {{
    font-size: 1.6rem;
}}

.detail-copy {{
    color: var(--text-muted);
    font-size: 0.97rem;
    line-height: 1.6;
    margin-top: 0.6rem;
}}

.detail-copy.tight {{
    margin-top: 0.4rem;
}}

.selection-empty {{
    min-height: 560px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
}}

.selection-empty .detail-copy {{
    max-width: 18rem;
    margin-left: auto;
    margin-right: auto;
}}

.empty-glyph {{
    color: rgba(184, 130, 15, 0.24);
    font-size: 3rem;
    line-height: 1;
    margin-top: 1.4rem;
}}

.identity-line {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-family: var(--font-mono);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    font-size: 0.76rem;
    margin-top: 0.75rem;
}}

.status-dot {{
    width: 0.65rem;
    height: 0.65rem;
    border-radius: 999px;
    display: inline-block;
    flex: 0 0 0.65rem;
}}

.mono-line {{
    font-family: var(--font-mono);
    font-size: 0.78rem;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-top: 0.7rem;
}}

.vision-row {{
    display: flex;
    align-items: center;
    gap: 0.55rem;
    font-size: 0.92rem;
    line-height: 1.35;
    padding: 0.48rem 0;
    border-top: 1px solid rgba(225, 220, 205, 0.6);
}}

.vision-row:first-of-type {{
    border-top: 0;
    padding-top: 0.1rem;
}}

.vision-dot {{
    width: 0.5rem;
    height: 0.5rem;
    border-radius: 999px;
    background: var(--vision);
    flex: 0 0 0.5rem;
}}

.vision-copy {{
    flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text-primary);
}}

.vision-meta {{
    flex: 0 0 auto;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-muted);
}}

.vision-summary {{
    margin-top: 0.8rem;
    color: var(--text-muted);
    font-size: 0.88rem;
    line-height: 1.55;
}}

.wound-row,
.intervention-row {{
    display: flex;
    justify-content: space-between;
    gap: 0.9rem;
    align-items: flex-start;
    padding: 0.5rem 0;
    border-top: 1px solid rgba(225, 220, 205, 0.6);
}}

.wound-row:first-of-type,
.intervention-row:first-of-type {{
    margin-top: 0.7rem;
}}

.wound-copy,
.intervention-copy {{
    color: var(--text-primary);
    font-size: 0.9rem;
    line-height: 1.45;
}}

.wound-meta,
.intervention-meta {{
    flex: 0 0 auto;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-muted);
    text-align: right;
}}

.muted-copy {{
    color: var(--text-muted);
    font-size: 0.92rem;
    line-height: 1.6;
}}

.audio-stub {{
    opacity: 0.4;
    min-height: 120px;
    position: relative;
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

.audio-slot-label {{
    position: relative;
    z-index: 1;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-muted);
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

.status-pill {{
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    font-family: var(--font-mono);
    font-size: 0.76rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--text-primary);
}}

.march-meta {{
    font-family: var(--font-mono);
    font-size: 0.76rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--text-muted);
}}

.note-copy {{
    margin-top: 0.85rem;
    color: var(--text-muted);
    font-size: 0.86rem;
    line-height: 1.55;
}}

.dashboard-link {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-top: 1.1rem;
    padding: 0.78rem 1rem;
    border-radius: 999px;
    border: 1px solid var(--gold);
    color: var(--gold);
    text-decoration: none;
    font-size: 0.92rem;
    transition: background 120ms ease, color 120ms ease, border-color 120ms ease;
}}

.dashboard-link:hover {{
    background: rgba(184, 130, 15, 0.06);
    color: #9e700d;
    border-color: #9e700d;
}}

@keyframes pulseRing {{
    0% {{
        opacity: 0.8;
        transform: scale(1);
    }}

    100% {{
        opacity: 0;
        transform: scale(2);
    }}
}}

@keyframes reticleSpin {{
    from {{
        transform: rotate(0deg);
    }}

    to {{
        transform: rotate(360deg);
    }}
}}

@media (max-width: 1100px) {{
    .tactical-layout {{
        grid-template-columns: 1fr;
    }}

    .selection-empty {{
        min-height: 280px;
    }}
}}
</style>
"""


def _ensure_seeded() -> None:
    if st.session_state.get("_demo_mode_selection") == "Live Vision":
        return
    if not app_state.get_roster():
        seed()


def _query_value(key: str) -> str | None:
    value = st.query_params.get(key)
    if isinstance(value, list):
        value = value[0] if value else None
    if value in (None, ""):
        return None
    return str(value)


def _sync_selection(valid_ids: set[str]) -> str | None:
    st.session_state.setdefault("selected_id", None)
    selected_query = _query_value("selected")
    if selected_query == "__clear__":
        st.session_state.selected_id = None
    elif selected_query is not None:
        st.session_state.selected_id = selected_query

    selected_id = st.session_state.selected_id
    if selected_id not in valid_ids | {"MEDIC"}:
        st.session_state.selected_id = None
    return st.session_state.selected_id


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


def _pretty_text(value: str) -> str:
    return value.replace("_", " ").strip().title()


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


def _best_confidence(casualty: Casualty) -> int:
    values = [float(getattr(wound, "ai_confidence", 0.0) or 0.0) for wound in casualty.wounds]
    values.extend(float(getattr(item, "confidence", 0.0) or 0.0) for item in casualty.ai_suggestions_log)
    return _format_percent(max(values, default=0.0))


def _vision_items(casualty: Casualty) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    seen_keys: set[tuple[str, str, int]] = set()

    for suggestion in casualty.ai_suggestions_log:
        if str(getattr(suggestion, "source", "")).lower() != "vision":
            continue
        text = str(getattr(suggestion, "suggestion", "")).strip()
        confidence = _format_percent(float(getattr(suggestion, "confidence", 0.0) or 0.0))
        key = ("vision", text, confidence)
        if key in seen_keys:
            continue
        rows.append({"text": text, "confidence": confidence})
        seen_keys.add(key)

    for pending in app_state.get_pending_suggestions():
        if pending.casualty_id != casualty.casualty_id or str(pending.source).lower() != "vision":
            continue
        raw = pending.raw
        text = str(getattr(raw, "suggestion", getattr(pending, "raw", ""))).strip()
        confidence = _format_percent(float(getattr(raw, "confidence", pending.confidence) or 0.0))
        key = ("vision", text, confidence)
        if key in seen_keys:
            continue
        rows.append({"text": text, "confidence": confidence})
        seen_keys.add(key)

    return rows


def _triage_status(casualty: Casualty) -> tuple[str, str]:
    category = casualty.triage_category
    if category == TriageCategory.DECEASED:
        return (TEXT_PRIMARY, "DECEASED")
    if category == TriageCategory.EXPECTANT:
        return (GRAY, "EXPECTANT")
    return (GREEN, "LIVE")


def _map_position_seed(casualty_id: str) -> int:
    return int(hashlib.md5(casualty_id.encode("utf-8")).hexdigest()[:8], 16)


def _distance_sq(point_a: tuple[int, int], point_b: tuple[int, int]) -> int:
    dx = point_a[0] - point_b[0]
    dy = point_a[1] - point_b[1]
    return (dx * dx) + (dy * dy)


def _stable_positions(casualties: list[Casualty]) -> dict[str, tuple[int, int]]:
    positions: dict[str, tuple[int, int]] = {}
    occupied = [(MEDIC_X, MEDIC_Y)]
    x_span = MAP_WIDTH - (SAFE_PADDING * 2)
    y_span = MAP_HEIGHT - (SAFE_PADDING * 2)

    for casualty in sorted(casualties, key=lambda item: item.casualty_id):
        seed_value = _map_position_seed(casualty.casualty_id)
        x = SAFE_PADDING + (seed_value % x_span)
        y = SAFE_PADDING + ((seed_value >> 11) % y_span)

        for step in range(24):
            candidate = (x, y)
            if all(_distance_sq(candidate, existing) >= 70 * 70 for existing in occupied):
                break
            x = SAFE_PADDING + ((x - SAFE_PADDING + 83 + (step * 17)) % x_span)
            y = SAFE_PADDING + ((y - SAFE_PADDING + 57 + (step * 11)) % y_span)

        positions[casualty.casualty_id] = (x, y)
        occupied.append((x, y))

    return positions


def _tooltip_position(x: int, y: int) -> tuple[int, int]:
    width = 220
    height = 86
    offset = 18
    left = x + offset if x <= MAP_WIDTH - width - 32 else x - width - offset
    top = y - height - offset if y >= MAP_HEIGHT - height - 32 else y + offset
    left = max(12, min(MAP_WIDTH - width - 12, left))
    top = max(12, min(MAP_HEIGHT - height - 12, top))
    return (left, top)


def _tooltip_html(casualty: Casualty, x: int, y: int) -> str:
    tooltip_x, tooltip_y = _tooltip_position(x, y)
    wound_count = len(casualty.wounds)
    title = f"{casualty.casualty_id} · {triage_label(casualty.triage_category)}"
    subtitle = f"{wound_count} wounds · top: {_top_wound_label(casualty)}"
    meta = f"AI · {_best_confidence(casualty)}%"
    return f"""
    <foreignObject class="tooltip-fo" x="{tooltip_x}" y="{tooltip_y}" width="220" height="86">
        <div xmlns="http://www.w3.org/1999/xhtml" class="tooltip-card">
            <div class="tooltip-title">{html.escape(title)}</div>
            <div class="tooltip-copy">{html.escape(subtitle)}</div>
            <div class="tooltip-meta">{html.escape(meta)}</div>
        </div>
    </foreignObject>
    """


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


def _corner_markers() -> str:
    markers = []
    for x, y in ((100, 100), (900, 100), (100, 500), (900, 500)):
        markers.append(
            f"""
            <line x1="{x - 5}" y1="{y}" x2="{x + 5}" y2="{y}" stroke="{GOLD}" stroke-width="1.5" />
            <line x1="{x}" y1="{y - 5}" x2="{x}" y2="{y + 5}" stroke="{GOLD}" stroke-width="1.5" />
            """
        )
    return "".join(markers)


def _selection_link(selected_id: str) -> str:
    return f"?selected={html.escape(selected_id)}"


def _map_svg(casualties: list[Casualty], selected_id: str | None) -> str:
    positions = _stable_positions(casualties)
    immediate_count = sum(1 for casualty in casualties if casualty.triage_category == TriageCategory.IMMEDIATE)
    delayed_count = sum(1 for casualty in casualties if casualty.triage_category == TriageCategory.DELAYED)
    status_text = (
        f"{len(casualties)} CASUALTIES · {immediate_count} IMMEDIATE · "
        f"{delayed_count} DELAYED · MEDIC ON SCENE"
    )
    timestamp = datetime.now().astimezone().strftime("%H:%M:%S")
    selected_line = ""

    if selected_id and selected_id in positions:
        selected_x, selected_y = positions[selected_id]
        selected_line = (
            f'<line x1="{MEDIC_X}" y1="{MEDIC_Y}" x2="{selected_x}" y2="{selected_y}" '
            f'stroke="{GOLD}" stroke-width="1" stroke-dasharray="4 4" opacity="0.5" />'
        )

    casualty_groups = []
    for casualty in casualties:
        x, y = positions[casualty.casualty_id]
        label_y = y - 20
        category_style = TRIAGE_MARK_STYLES.get(casualty.triage_category, TRIAGE_MARK_STYLES[TriageCategory.UNASSESSED])
        pulse_ring = ""
        selected_ring = ""
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
            pulse_ring = (
                f'<circle class="pulse-ring" cx="{x}" cy="{y}" r="12" fill="none" stroke="{RED}" stroke-width="1.5" />'
            )
        if casualty.casualty_id == selected_id:
            selected_ring = f"""
            <circle class="selected-ring" cx="{x}" cy="{y}" r="18" fill="none" stroke="{GOLD}" stroke-width="2" />
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
                    {pulse_ring}
                    {selected_ring}
                    {marker}
                    <text class="map-label" x="{x}" y="{label_y}" text-anchor="middle">{html.escape(casualty.casualty_id)} · {html.escape(triage_label(casualty.triage_category))}</text>
                </a>
                {_tooltip_html(casualty, x, y)}
            </g>
            """
        )

    svg_markup = f"""
    <svg viewBox="0 0 {MAP_WIDTH} {MAP_HEIGHT}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="AEGIS tactical map">
        <rect x="0" y="0" width="{MAP_WIDTH}" height="{MAP_HEIGHT}" fill="{BACKGROUND}" />
        <a href="?selected=__clear__" target="_self">
            <rect x="0" y="0" width="{MAP_WIDTH}" height="{MAP_HEIGHT}" fill="transparent" />
        </a>
        <g class="map-grid">
            {_grid_lines(50, "#E8E4D8", 1)}
            {_grid_lines(250, "#D8D4C8", 1.5)}
        </g>
        <g class="map-corners">{_corner_markers()}</g>
        <text class="map-grid-label" x="24" y="26">GRID 38TKL 042 119</text>
        <text class="map-status" x="976" y="26" text-anchor="end">{html.escape(status_text)}</text>
        {selected_line}
        <g class="map-contact medic-group">
            <a class="map-link" href="{_selection_link('MEDIC')}" target="_self">
                <circle class="hover-glow" cx="{MEDIC_X}" cy="{MEDIC_Y}" r="20" fill="{GOLD}" />
                <rect class="medic-diamond" x="{MEDIC_X - 8}" y="{MEDIC_Y - 8}" width="16" height="16" rx="1.5" fill="{GOLD}" transform="rotate(45 {MEDIC_X} {MEDIC_Y})" />
                <text class="medic-label" x="{MEDIC_X}" y="{MEDIC_Y + 26}" text-anchor="middle">MEDIC · SGT HAYES</text>
            </a>
        </g>
        <g class="map-casualties">
            {''.join(casualty_groups)}
        </g>
        <text class="map-footer" x="24" y="578">STYLIZED OVERHEAD · {timestamp}</text>
        <text class="map-footer" x="976" y="578" text-anchor="end" fill="{GOLD}">AEGIS ◆</text>
    </svg>
    """
    return re.sub(r">\s+<", "><", svg_markup).strip()


def _empty_panel() -> str:
    return f"""
    <section class="tactical-card detail-shell selection-empty">
        <div>
            <div class="detail-title small">Select a casualty</div>
            <div class="detail-copy">Click any icon on the map to see their status.</div>
            <div class="empty-glyph">◆</div>
        </div>
    </section>
    """


def _medic_panel() -> str:
    return f"""
    <section class="tactical-card detail-shell">
        <div class="detail-section">
            <div class="section-kicker">MEDIC · SGT HAYES</div>
            <div class="detail-title small">Combat Medic</div>
            <div class="detail-copy">Live perception feed on main dashboard.</div>
            <a class="dashboard-link" href="/" target="_self">Open dashboard view</a>
        </div>
    </section>
    """


def _vision_section(casualty: Casualty) -> str:
    vision_items = _vision_items(casualty)
    wounds = list(casualty.wounds)
    rows: list[str] = []

    for item in vision_items:
        rows.append(
            f"""
            <div class="vision-row">
                <span class="vision-dot"></span>
                <div class="vision-copy" title="{html.escape(str(item['text']))}">{html.escape(str(item['text']))}</div>
                <div class="vision-meta">AI · {item['confidence']}%</div>
            </div>
            """
        )

    wound_rows = []
    if wounds:
        bleeding_count = sum(1 for wound in wounds if bool(getattr(wound, "active_bleeding", False)))
        wound_rows.append(
            f'<div class="vision-summary">{len(wounds)} wounds detected · {bleeding_count} bleeding</div>'
        )
        for wound in wounds[:3]:
            wound_rows.append(
                f"""
                <div class="wound-row">
                    <div class="wound-copy">{html.escape(_pretty_text(getattr(wound, 'location', 'unknown')))} · {html.escape(_pretty_text(getattr(wound, 'severity', 'unknown')))}</div>
                    <div class="wound-meta">{float(getattr(wound, 'area_cm2', 0.0) or 0.0):.1f} cm²</div>
                </div>
                """
            )

    if not rows and not wounds:
        rows.append('<div class="muted-copy">No vision data yet</div>')

    return f"""
    <div class="detail-section">
        <div class="section-kicker">VISION</div>
        {''.join(rows)}
        {''.join(wound_rows)}
    </div>
    """


def _audio_section() -> str:
    return """
    <div class="detail-section audio-stub">
        <div class="section-kicker">AUDIO</div>
        <div class="audio-slot waveform"><span class="audio-slot-label">WAVEFORM</span></div>
        <div class="audio-slot compact"><span class="audio-slot-label">RESP STATUS · awaiting pipeline</span></div>
        <div class="audio-slot compact"><span class="audio-slot-label">TRANSCRIPT · —</span></div>
        <div class="audio-awaiting">AWAITING NEAL</div>
    </div>
    """


def _interventions_section(casualty: Casualty) -> str:
    intervention_rows = []
    if casualty.interventions:
        for intervention in casualty.interventions:
            intervention_rows.append(
                f"""
                <div class="intervention-row">
                    <div class="intervention-copy">{html.escape(_pretty_text(getattr(intervention, 'type', 'unknown')))} · {html.escape(_pretty_text(getattr(intervention, 'location', 'unknown')))}</div>
                    <div class="intervention-meta">{_format_timestamp(getattr(intervention, 'timestamp', None))}</div>
                </div>
                """
            )
    else:
        intervention_rows.append('<div class="muted-copy">None logged</div>')

    live_color, live_label = _triage_status(casualty)
    march_total = sum(1 for value in casualty.march_checklist.values() if bool(value))
    notes = (
        f'<div class="note-copy">{html.escape(casualty.medic_notes)}</div>'
        if casualty.medic_notes
        else ""
    )
    return f"""
    <div class="detail-section">
        <div class="section-kicker">INTERVENTIONS</div>
        {''.join(intervention_rows)}
        <div class="status-bar">
            <div class="status-pill"><span class="status-dot" style="background:{live_color};"></span>{html.escape(live_label)}</div>
            <div class="march-meta">MARCH · {march_total}/5</div>
        </div>
        {notes}
    </div>
    """


def _casualty_panel(casualty: Casualty) -> str:
    triage_text = triage_label(casualty.triage_category)
    triage_color = TRIAGE_MARK_STYLES.get(casualty.triage_category, TRIAGE_MARK_STYLES[TriageCategory.UNASSESSED])[
        "fill"
    ]
    if casualty.triage_category == TriageCategory.UNASSESSED:
        triage_color = GRAY

    return f"""
    <section class="tactical-card detail-shell">
        <div class="detail-section">
            <div class="detail-title">Casualty {html.escape(casualty.casualty_id)}</div>
            <div class="identity-line">
                <span class="status-dot" style="background:{triage_color};"></span>
                {html.escape(triage_text)}
            </div>
            <div class="mono-line">LAST SEEN · {_format_timestamp(casualty.last_seen)}</div>
        </div>
        {_vision_section(casualty)}
        {_audio_section()}
        {_interventions_section(casualty)}
    </section>
    """


def _detail_panel(selected_id: str | None, casualties: dict[str, Casualty]) -> str:
    if not selected_id:
        return _empty_panel()
    if selected_id == "MEDIC":
        return _medic_panel()
    casualty = casualties.get(selected_id)
    if casualty is None:
        return _empty_panel()
    return _casualty_panel(casualty)


def _page_html(casualties: list[Casualty], selected_id: str | None) -> str:
    casualty_map = {casualty.casualty_id: casualty for casualty in casualties}
    page_markup = f"""
    <div class="tactical-layout">
        <section class="tactical-card map-shell">
            {_map_svg(casualties, selected_id)}
        </section>
        {_detail_panel(selected_id, casualty_map)}
    </div>
    """
    return re.sub(r">\s+<", "><", page_markup).strip()


st.set_page_config(page_title="AEGIS Tactical Map", layout="wide")
st.markdown(STYLE_BLOCK, unsafe_allow_html=True)
_ensure_seeded()

with st.sidebar:
    controls()


@st.fragment(run_every=0.5)
def render_tactical_map() -> None:
    casualties = app_state.get_roster()
    selected_id = _sync_selection({casualty.casualty_id for casualty in casualties})
    st.markdown(_page_html(casualties, selected_id), unsafe_allow_html=True)


render_tactical_map()
