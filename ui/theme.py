from __future__ import annotations

from schema import TriageCategory

MAIN_BG = "#0a0a0a"
SIDEBAR_BG = "#141414"
PANEL_BG = "#111111"
PANEL_ALT_BG = "#171717"
BORDER = "#232325"
TEXT_PRIMARY = "#f5f5f7"
TEXT_MUTED = "#8e8e93"
TEXT_SOFT = "#c7c7cc"
RED = "#ff3b30"
YELLOW = "#ffcc00"
GREEN = "#34c759"
GRAY = "#8e8e93"
BLACK = "#3a3a3c"
WHITE = "#f5f5f7"
ACCENT_BLUE = "#5ac8fa"
ACCENT_PURPLE = "#bf5af2"

TRIAGE_COLORS = {
    TriageCategory.IMMEDIATE: RED,
    TriageCategory.DELAYED: YELLOW,
    TriageCategory.MINIMAL: GREEN,
    TriageCategory.EXPECTANT: GRAY,
    TriageCategory.DECEASED: BLACK,
    TriageCategory.UNASSESSED: WHITE,
}

SOURCE_COLORS = {
    "vision": ACCENT_BLUE,
    "audio": ACCENT_PURPLE,
    "fusion": YELLOW,
}

TRIAGE_LABELS = {
    TriageCategory.IMMEDIATE: "IMMEDIATE",
    TriageCategory.DELAYED: "DELAYED",
    TriageCategory.MINIMAL: "MINIMAL",
    TriageCategory.EXPECTANT: "EXPECTANT",
    TriageCategory.DECEASED: "DECEASED",
    TriageCategory.UNASSESSED: "UNASSESSED",
}

GLOBAL_CSS = f"""
<style>
    html, body, [class*="css"] {{
        font-family: "JetBrains Mono", "SFMono-Regular", "Menlo", "Consolas", monospace;
    }}

    .stApp {{
        background: {MAIN_BG};
        color: {TEXT_PRIMARY};
    }}

    [data-testid="stSidebar"] {{
        background: {SIDEBAR_BG};
        border-right: 1px solid {BORDER};
    }}

    [data-testid="stSidebar"] * {{
        color: {TEXT_PRIMARY};
    }}

    .block-container {{
        padding-top: 1rem;
        padding-bottom: 1rem;
    }}

    .aegis-panel {{
        background: linear-gradient(180deg, {PANEL_ALT_BG} 0%, {PANEL_BG} 100%);
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 1rem;
        min-height: 100%;
        box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.02) inset;
    }}

    .aegis-kicker {{
        color: {TEXT_MUTED};
        font-size: 0.78rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.4rem;
    }}

    .aegis-title {{
        color: {TEXT_PRIMARY};
        font-size: 1.05rem;
        font-weight: 700;
        margin-bottom: 0.35rem;
    }}

    .aegis-subtle {{
        color: {TEXT_MUTED};
        font-size: 0.85rem;
    }}

    .aegis-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.75rem;
        padding: 0.7rem 0.85rem;
        border: 1px solid {BORDER};
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.015);
        margin-bottom: 0.6rem;
    }}

    .aegis-row:last-child {{
        margin-bottom: 0;
    }}

    .aegis-badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        border-radius: 999px;
        padding: 0.2rem 0.55rem;
        font-size: 0.78rem;
        font-weight: 700;
    }}

    .aegis-list-title {{
        color: {TEXT_PRIMARY};
        font-weight: 700;
    }}

    .aegis-list-meta {{
        color: {TEXT_MUTED};
        font-size: 0.8rem;
        margin-top: 0.15rem;
    }}

    .aegis-empty {{
        border: 1px dashed {BORDER};
        border-radius: 12px;
        padding: 1rem;
        color: {TEXT_MUTED};
        text-align: center;
        background: rgba(255, 255, 255, 0.01);
    }}

    .aegis-video-shell {{
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 0.75rem;
        background: rgba(255, 255, 255, 0.015);
    }}

    .aegis-medevac-item {{
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 0.75rem;
        background: rgba(255, 255, 255, 0.015);
    }}

    .aegis-medevac-label {{
        color: {TEXT_MUTED};
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.35rem;
    }}

    .aegis-medevac-value {{
        color: {TEXT_PRIMARY};
        font-size: 0.92rem;
    }}
</style>
"""


def triage_color(triage: TriageCategory) -> str:
    return TRIAGE_COLORS.get(triage, TEXT_MUTED)


def triage_label(triage: TriageCategory) -> str:
    return TRIAGE_LABELS.get(triage, str(triage))


def source_color(source: str) -> str:
    return SOURCE_COLORS.get(source.lower(), TEXT_MUTED)
