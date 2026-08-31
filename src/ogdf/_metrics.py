"""Drawing-quality metrics: compare layouts on numbers, not by eye.

A layout is easy to admire and hard to judge. These helpers turn a drawing into
figures you can rank, regression-test, and put in a table: how many edges cross,
how evenly long they are, how much space the drawing uses, how well the geometry
reproduces graph distances.

Every metric describes the *drawing*, so it depends on the `GraphAttributes`
you pass, not on the graph alone. Run a layout first.

    >>> import ogdf
    >>> g = ogdf.Graph()
    >>> ogdf.complete_graph(g, 5)
    >>> ga = ogdf.GraphAttributes(g)
    >>> ogdf.CircularLayout().call(ga)
    >>> ogdf.drawing_metrics(ga)["crossings"]
    5

The pairwise metrics are quadratic - crossings in the number of edges, node
overlap and stress in the number of nodes - so treat `drawing_metrics` as
something to run on a drawing you are inspecting, not inside a hot loop.
"""

from __future__ import annotations

import math
import statistics
from typing import Any, cast

from ogdf import _core

__all__ = ["compare_layouts", "drawing_metrics"]


def drawing_metrics(attributes) -> dict[str, Any]:
    """Measure a drawing, returning every metric in one dict.

    Keys:

    - `nodes`, `edges` - the graph's size, for context.
    - `crossings` - edge crossings in the drawing.
    - `edge_length_min` / `_max` / `_mean` / `_stdev` - the length distribution.
    - `edge_length_cv` - standard deviation over mean, a scale-free measure of
      how uneven the edges are. 0 means perfectly uniform; `None` when the mean
      is 0 or there are too few edges to have a deviation.
    - `width`, `height`, `area` - the drawing's extent, node boxes and bend
      points included.
    - `aspect_ratio` - the longer side over the shorter, so always >= 1;
      `None` for a degenerate drawing with no extent.
    - `node_overlap_pairs`, `node_overlap_area` - overlapping node boxes. Both
      are 0 when node sizes were never set.
    - `min_angle` - angular resolution in radians, `None` if no node has two or
      more non-loop edges; `min_angle_degrees` is the same in degrees.
    - `stress` - scale-normalized deviation from graph distances. Lower is
      better; 0 is a perfect embedding of the hop metric.

    Returned as a plain dict of plain numbers, so it is directly serializable
    and easy to put in a table alongside `ogdf.provenance()`.
    """
    graph = attributes.graph
    lengths = _core.edge_lengths(attributes)
    min_x, min_y, max_x, max_y = _core.bounding_box(attributes)
    overlap_pairs, overlap_area = _core.node_overlaps(attributes)
    # None when no node has two or more non-loop edges. The binding returns an
    # optional, which nanobind's generated stub widens to `object`.
    raw_angle = cast("float | None", _core.min_angle(attributes))
    angle = None if raw_angle is None else float(raw_angle)

    width = max_x - min_x
    height = max_y - min_y
    mean = statistics.fmean(lengths) if lengths else 0.0
    stdev = statistics.stdev(lengths) if len(lengths) > 1 else 0.0
    shorter, longer = sorted((width, height))

    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "crossings": _core.count_crossings(attributes),
        "edge_length_min": min(lengths) if lengths else 0.0,
        "edge_length_max": max(lengths) if lengths else 0.0,
        "edge_length_mean": mean,
        "edge_length_stdev": stdev,
        "edge_length_cv": (stdev / mean) if (mean > 0.0 and len(lengths) > 1) else None,
        "width": width,
        "height": height,
        "area": width * height,
        "aspect_ratio": (longer / shorter) if shorter > 0.0 else None,
        "node_overlap_pairs": overlap_pairs,
        "node_overlap_area": overlap_area,
        "min_angle": angle,
        "min_angle_degrees": math.degrees(angle) if angle is not None else None,
        "stress": _core.stress(attributes),
    }


def compare_layouts(
    graph,
    layouts,
    *,
    attributes_flags: int | None = None,
    seed: int | None = None,
) -> list[dict[str, Any]]:
    """Run several layouts on one graph and measure each, best-first.

    `layouts` maps a name to either a layout instance or a zero-argument factory
    returning one; a factory is the right choice when you want to configure the
    layout. Each entry gets a fresh `GraphAttributes`, so the runs cannot
    contaminate one another.

    Pass `seed` to make the randomized layouts reproducible - each run is seeded
    identically, so the comparison is like for like rather than luck of the
    draw.

    A layout that rejects this graph (`InvalidGraphError`, because its
    preconditions are unmet) is reported with an `error` key instead of metrics
    rather than aborting the comparison - the usual reason to compare layouts is
    that you do not yet know which ones apply.

    Results are sorted by crossings, then stress, so the most readable candidate
    comes first; entries that errored sort last.

    >>> import ogdf
    >>> g = ogdf.Graph()
    >>> ogdf.complete_graph(g, 6)
    >>> rows = ogdf.compare_layouts(
    ...     g, {"circular": ogdf.CircularLayout, "planar": ogdf.SchnyderLayout},
    ...     seed=1,
    ... )
    >>> rows[-1]["layout"], "error" in rows[-1]
    ('planar', True)
    """
    flags = _core.ALL_ATTRIBUTES if attributes_flags is None else attributes_flags
    rows: list[dict[str, Any]] = []
    for name, layout in layouts.items():
        attributes = _core.GraphAttributes(graph, flags)
        instance = layout() if callable(layout) else layout
        try:
            if seed is None:
                instance.call(attributes)
            else:
                _core.seed_random_engine(seed)
                instance.call(attributes)
        except _core.OGDFError as exc:
            rows.append({"layout": name, "error": str(exc)})
            continue
        rows.append({"layout": name, **drawing_metrics(attributes)})

    def rank(row):
        if "error" in row:
            return (1, 0.0, 0.0)
        return (0, float(row["crossings"]), float(row["stress"]))

    rows.sort(key=rank)
    return rows
