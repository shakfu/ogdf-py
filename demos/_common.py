"""Shared helpers for the demos (output directory and color helpers)."""

import colorsys
from pathlib import Path

import ogdf


def output_dir() -> Path:
    """Return build/demo-output (created if needed), next to the repo root."""
    root = Path(__file__).resolve().parent.parent
    out = root / "build" / "demo-output"
    out.mkdir(parents=True, exist_ok=True)
    return out


def palette(n: int) -> list[ogdf.Color]:
    """Return n visually distinct colors (evenly spaced hues)."""
    n = max(n, 1)
    colors = []
    for i in range(n):
        r, g, b = colorsys.hsv_to_rgb(i / n, 0.65, 0.95)
        colors.append(ogdf.Color(int(r * 255), int(g * 255), int(b * 255)))
    return colors


def gradient_color(t: float) -> ogdf.Color:
    """Map t in [0, 1] to a green (near) -> red (far) gradient color."""
    t = max(0.0, min(1.0, t))
    r, g, b = colorsys.hsv_to_rgb((1.0 - t) * 0.33, 0.75, 0.95)
    return ogdf.Color(int(r * 255), int(g * 255), int(b * 255))
