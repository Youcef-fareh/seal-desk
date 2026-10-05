"""
Seal Desktop - Theme / Design System
Centralises all colors, fonts, and spacing tokens.
"""

from __future__ import annotations

# ──────────────────────────────────────────────────────────────────────────────
# Color Palette  (Dark-first, Material-inspired + Violet accent)
# ──────────────────────────────────────────────────────────────────────────────

PALETTE = {
    # Background layers
    "bg_0": "#0D0D0F",  # deepest background (window)
    "bg_1": "#141417",  # card / panel background
    "bg_2": "#1C1C22",  # elevated surface
    "bg_3": "#24242D",  # hover / active surface
    "bg_4": "#2E2E3A",  # selected / focused
    # Text
    "text_primary": "#F0EFFE",
    "text_secondary": "#A0A0B8",
    "text_tertiary": "#606078",
    "text_disabled": "#404050",
    # Accent (violet)
    "accent": "#8B5CF6",
    "accent_hover": "#7C3AED",
    "accent_dim": "#3B1F7A",
    "accent_light": "#C4B5FD",
    # Semantic
    "success": "#22C55E",
    "warning": "#F59E0B",
    "error": "#EF4444",
    "info": "#3B82F6",
    # Borders / Separators
    "border": "#2A2A38",
    "divider": "#1E1E28",
    # Progress bar
    "progress_track": "#1C1C28",
    "progress_fill": "#8B5CF6",
    # Scrollbar
    "scrollbar": "#2E2E40",
    "scrollbar_hover": "#3E3E54",
    # Button variants
    "btn_primary": "#8B5CF6",
    "btn_primary_hover": "#7C3AED",
    "btn_primary_active": "#6D28D9",
    "btn_secondary": "#24242D",
    "btn_secondary_hover": "#2E2E3A",
    "btn_danger": "#DC2626",
    "btn_danger_hover": "#B91C1C",
    # Entry / Input
    "entry_bg": "#1C1C22",
    "entry_border": "#3A3A50",
    "entry_border_focus": "#8B5CF6",
}

# Light-mode overrides (WIP — not yet wired to UI toggle)
LIGHT_OVERRIDES = {
    "bg_0": "#F4F4F8",
    "bg_1": "#FFFFFF",
    "bg_2": "#EDEDF4",
    "bg_3": "#E0E0EC",
    "bg_4": "#D4D4E4",
    "text_primary": "#0D0D1A",
    "text_secondary": "#4A4A60",
    "text_tertiary": "#888898",
    "border": "#D0D0E0",
    "divider": "#E8E8F0",
    "entry_bg": "#FFFFFF",
    "entry_border": "#C4C4D8",
    "progress_track": "#E0E0EC",
}


def get_palette(dark: bool = True) -> dict[str, str]:
    p = dict(PALETTE)
    if not dark:
        p.update(LIGHT_OVERRIDES)
    return p


# ──────────────────────────────────────────────────────────────────────────────
# Typography
# ──────────────────────────────────────────────────────────────────────────────

FONTS = {
    "display": ("Segoe UI", 28, "bold"),
    "heading1": ("Segoe UI", 20, "bold"),
    "heading2": ("Segoe UI", 16, "bold"),
    "heading3": ("Segoe UI", 14, "bold"),
    "body": ("Segoe UI", 13, "normal"),
    "body_sm": ("Segoe UI", 11, "normal"),
    "caption": ("Segoe UI", 10, "normal"),
    "mono": ("Consolas", 12, "normal"),
    "mono_sm": ("Consolas", 11, "normal"),
}

# ──────────────────────────────────────────────────────────────────────────────
# Spacing / Layout
# ──────────────────────────────────────────────────────────────────────────────

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 16,
    "lg": 24,
    "xl": 32,
    "2xl": 48,
}

RADIUS = {
    "sm": 6,
    "md": 10,
    "lg": 14,
    "xl": 20,
    "full": 999,
}

SIDEBAR_WIDTH = 220
TOPBAR_HEIGHT = 60
