from __future__ import annotations

import html

from schema import TriageCategory

BACKGROUND = "#F5F2EB"
SURFACE = "#FAFAF6"
SURFACE_SOFT = "#F8F5EE"
BORDER = "#E8E4D8"
DIVIDER = "#E1DCCD"
TEXT_PRIMARY = "#1A1A1A"
TEXT_MUTED = "#7A7668"
TEXT_SOFT = "#9A9588"
GOLD = "#B8820F"
GOLD_SOFT = "#E7D5AB"
RED = "#C8302D"
AMBER = "#D4A92B"
GREEN = "#3F7C4F"
GRAY = "#8A8680"
BLACK = "#1C1B1A"
WHITE = "#F5F2EB"
VISION_BLUE = "#5C7FA3"
AUDIO_PURPLE = "#7B68A6"
FUSION_GOLD = GOLD
SHADOW = "0 10px 28px rgba(84, 69, 39, 0.08)"

FONT_SERIF_DISPLAY = '"Playfair Display", "Canela", "GT Super", "Tiempos Text", Georgia, "Times New Roman", serif'
FONT_MONO = '"JetBrains Mono", "IBM Plex Mono", "SFMono-Regular", Menlo, Consolas, monospace'
FONT_SANS = '"Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'

SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 16
SPACE_LG = 24
SPACE_XL = 40

TRIAGE_COLORS = {
    TriageCategory.IMMEDIATE: RED,
    TriageCategory.DELAYED: AMBER,
    TriageCategory.MINIMAL: GREEN,
    TriageCategory.EXPECTANT: GRAY,
    TriageCategory.DECEASED: BLACK,
    TriageCategory.UNASSESSED: WHITE,
}

TRIAGE_CLASSES = {
    TriageCategory.IMMEDIATE: "triage-immediate",
    TriageCategory.DELAYED: "triage-delayed",
    TriageCategory.MINIMAL: "triage-minimal",
    TriageCategory.EXPECTANT: "triage-expectant",
    TriageCategory.DECEASED: "triage-deceased",
    TriageCategory.UNASSESSED: "triage-unassessed",
}

TRIAGE_LABELS = {
    TriageCategory.IMMEDIATE: "IMMEDIATE",
    TriageCategory.DELAYED: "DELAYED",
    TriageCategory.MINIMAL: "MINIMAL",
    TriageCategory.EXPECTANT: "EXPECTANT",
    TriageCategory.DECEASED: "DECEASED",
    TriageCategory.UNASSESSED: "UNASSESSED",
}

SOURCE_COLORS = {
    "vision": VISION_BLUE,
    "audio": AUDIO_PURPLE,
    "fusion": FUSION_GOLD,
}


def triage_color(category: TriageCategory) -> str:
    return TRIAGE_COLORS.get(category, TEXT_MUTED)


def triage_label(category: TriageCategory) -> str:
    return TRIAGE_LABELS.get(category, str(category))


def triage_dot(category: TriageCategory) -> str:
    css_class = TRIAGE_CLASSES.get(category, "triage-unassessed")
    return f'<span class="triage-dot {css_class}">●</span>'


def hud_label(text: str) -> str:
    return f'<span class="hud-label">{html.escape(text.upper())}</span>'


def source_color(source: str) -> str:
    return SOURCE_COLORS.get(source.lower(), GOLD)


def source_dot(source: str) -> str:
    color = source_color(source)
    return f'<span class="source-dot" style="color:{color};">●</span>'
