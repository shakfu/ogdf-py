"""Coordinate transforms: get a finished drawing onto a page.

Layouts produce coordinates in whatever range suits their algorithm - FMMM
centres its result near the origin, the planar grid layouts start at (0, 0) and
grow, and a disconnected graph can come back with its components stacked on top
of one another. Placing that result is a separate job from computing it.

    >>> import ogdf
    >>> g = ogdf.Graph()
    >>> ogdf.complete_graph(g, 6)
    >>> ga = ogdf.GraphAttributes(g)
    >>> ogdf.CircularLayout().call(ga)
    >>> factor = ogdf.fit_to_box(ga, 800, 600, margin=20)
    >>> x0, y0, x1, y1 = ogdf.bounding_box(ga)
    >>> round(x1 - x0) <= 760 and round(y1 - y0) <= 560
    True

Every transform moves edge bend points along with node coordinates, so a
drawing whose edges were routed (orthogonal, planarization) survives intact.
All of them mutate the `GraphAttributes` in place, matching how layouts behave.
"""

from __future__ import annotations

from typing import Any

from ogdf import _core

__all__ = [
    "center",
    "fit_to_box",
    "normalize",
    "pack_components",
    "scale",
    "translate",
]


def _anchor(attributes, about) -> tuple[float, float]:
    """Resolve the `about` argument of `scale` to a concrete point."""
    if about == "origin":
        return (0.0, 0.0)
    min_x, min_y, max_x, max_y = _core.bounding_box(attributes)
    if about == "center":
        return ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)
    if about == "min":
        return (min_x, min_y)
    if isinstance(about, (tuple, list)) and len(about) == 2:
        return (float(about[0]), float(about[1]))
    raise ValueError(
        f"about must be 'center', 'origin', 'min', or an (x, y) point, got {about!r}"
    )


def translate(attributes, dx: float, dy: float) -> None:
    """Move the whole drawing by (dx, dy)."""
    _core.translate_drawing(attributes, float(dx), float(dy))


def scale(
    attributes,
    factor: float,
    factor_y: float | None = None,
    *,
    about: Any = "center",
    scale_node_sizes: bool = False,
) -> None:
    """Scale the drawing by `factor` (and `factor_y`, if the axes differ).

    `about` is the fixed point: `"center"` (the default) keeps the drawing where
    it is and grows it outward, `"origin"` scales coordinates directly,
    `"min"` pins the lower-left corner, or pass an explicit `(x, y)`.

    `scale_node_sizes` is False by default, so this spreads nodes apart without
    making them bigger - which is what you want when nodes overlap. Set it True
    to scale the whole picture, node boxes included.

    >>> import ogdf
    >>> g, m = ogdf.from_edges([("a", "b")])
    >>> ga = ogdf.GraphAttributes(g)
    >>> ga.set_x(m["b"], 10.0)
    >>> ogdf.scale(ga, 2.0, about="origin")
    >>> ga.x(m["b"])
    20.0
    """
    sx = float(factor)
    sy = sx if factor_y is None else float(factor_y)
    cx, cy = _anchor(attributes, about)
    _core.scale_drawing(attributes, sx, sy, cx, cy, scale_node_sizes)


def center(attributes, x: float = 0.0, y: float = 0.0) -> None:
    """Move the drawing so its bounding box is centred on (x, y)."""
    min_x, min_y, max_x, max_y = _core.bounding_box(attributes)
    translate(
        attributes,
        x - (min_x + max_x) / 2.0,
        y - (min_y + max_y) / 2.0,
    )


def normalize(attributes) -> None:
    """Move the drawing so its lower-left corner sits at the origin.

    Coordinates become non-negative, which is what most renderers and file
    formats expect. This only translates - it never rescales - so distances and
    the drawing's proportions are untouched.
    """
    min_x, min_y, _, _ = _core.bounding_box(attributes)
    translate(attributes, -min_x, -min_y)


def fit_to_box(
    attributes,
    width: float,
    height: float,
    *,
    margin: float = 0.0,
    scale_node_sizes: bool = True,
    center_in_box: bool = True,
) -> float:
    """Scale and place the drawing to fit a `width` x `height` box.

    Returns the scale factor applied. Aspect ratio is always preserved - the
    drawing is fitted to whichever axis binds first - so the result fills one
    dimension and is centred in the other (unless `center_in_box` is False, in
    which case it is pinned to the lower-left).

    `margin` is space left inside the box on every side.

    `scale_node_sizes` defaults to True, which scales the whole picture and
    makes the fit exact. Set it False to keep node boxes at their current size
    while the layout shrinks around them; the fit is still exact - the factor is
    solved for rather than estimated - but the nodes will take up
    proportionally more room, and a box too small to hold them at their fixed
    size yields a factor of 0.

    >>> import ogdf
    >>> g = ogdf.Graph()
    >>> ogdf.complete_graph(g, 5)
    >>> ga = ogdf.GraphAttributes(g)
    >>> ogdf.CircularLayout().call(ga)
    >>> factor = ogdf.fit_to_box(ga, 400, 400, margin=10)
    >>> x0, y0, x1, y1 = ogdf.bounding_box(ga)
    >>> round(x0, 6) >= 10 and round(x1, 6) <= 390
    True
    """
    if width <= 0.0 or height <= 0.0:
        raise _core.PreconditionError("fit_to_box: width and height must be positive")
    inner_width = width - 2.0 * margin
    inner_height = height - 2.0 * margin
    if inner_width <= 0.0 or inner_height <= 0.0:
        raise _core.PreconditionError(
            f"fit_to_box: a margin of {margin} leaves no room inside {width} x {height}"
        )

    factor = _core.fit_scale(attributes, inner_width, inner_height, scale_node_sizes)
    if factor > 0.0 and factor != 1.0:
        scale(
            attributes,
            factor,
            about="origin",
            scale_node_sizes=scale_node_sizes,
        )
    if center_in_box:
        center(attributes, width / 2.0, height / 2.0)
    else:
        normalize(attributes)
        translate(attributes, margin, margin)
    return factor


def pack_components(
    attributes, *, separation: float = 20.0, page_ratio: float = 1.0
) -> int:
    """Arrange disconnected components side by side instead of overlapping.

    Several layouts place every connected component at the same origin, so a
    disconnected graph comes back as a pile. This spreads them out with OGDF's
    tile-to-rows packer and returns the number of components; a connected graph
    is left untouched.

    `separation` is the gap between neighbouring components, `page_ratio` the
    desired width/height of the arrangement.

    >>> import ogdf
    >>> g, m = ogdf.from_edges([("a", "b"), ("c", "d")])
    >>> ga = ogdf.GraphAttributes(g)
    >>> ogdf.pack_components(ga)
    2
    """
    return _core.tile_components(attributes, float(separation), float(page_ratio))
