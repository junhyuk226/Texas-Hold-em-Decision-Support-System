"""Theme-aware styling helpers for Streamlit's light and dark appearances."""
from __future__ import annotations

from typing import Any


def resolve_theme_type(streamlit_module: Any) -> str:
    """Read the active Streamlit appearance with a safe light fallback.

    Streamlit 1.65 exposes the active client appearance via st.context.theme.type.
    Streamlit documents that this value can briefly be stale on first load or
    immediately after a settings change. CSS in the app therefore uses live
    Streamlit theme tokens for surfaces and native controls; Plotly's dedicated
    palette is selected on script rerun.
    """
    try:
        theme = streamlit_module.context.theme
        value = getattr(theme, "type", None)
        if value is None:
            value = theme["type"]
        if str(value).lower() in {"light", "dark"}:
            return str(value).lower()
    except Exception:
        pass

    try:
        getter = getattr(streamlit_module, "get_option", None)
        value = getter("theme.base") if callable(getter) else None
        if str(value).lower() in {"light", "dark"}:
            return str(value).lower()
    except Exception:
        pass
    return "light"


def plotly_palette(theme_type: str) -> dict[str, str]:
    """Return a readable Plotly palette that matches Streamlit's appearance."""
    if str(theme_type).lower() == "dark":
        return {
            "template": "plotly_dark",
            "surface": "#1b2229",
            "text": "#edf3ef",
            "muted": "#b5c0ba",
            "grid": "#3a454d",
            "axis": "#75838b",
            "border": "#46545d",
            "green": "#4bd196",
            "green_fill": "rgba(75,209,150,0.13)",
            "amber": "#f2bd62",
            "blue": "#84adff",
            "red": "#f18a91",
            "neutral": "#aab5be",
            "hover_bg": "#26333b",
        }
    return {
        "template": "plotly_white",
        "surface": "#ffffff",
        "text": "#26382f",
        "muted": "#66766d",
        "grid": "#e5ece7",
        "axis": "#aab7af",
        "border": "#dce6df",
        "green": "#16845b",
        "green_fill": "rgba(22,132,91,0.11)",
        "amber": "#c88723",
        "blue": "#5077c8",
        "red": "#c85c64",
        "neutral": "#8b9690",
        "hover_bg": "#f6faf7",
    }
