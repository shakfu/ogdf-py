"""One call from a graph to a placed drawing.

The pieces are all available individually - pick a layout class, build a
`GraphAttributes`, check preconditions, seed, run, pack, fit. `layout()` is the
same sequence in one call, for when you do not need to interleave anything:

    >>> import ogdf
    >>> g = ogdf.Graph()
    >>> ogdf.complete_graph(g, 6)
    >>> ga = ogdf.layout(g, ogdf.CircularLayout, fit=(800, 600), margin=20)
    >>> x0, y0, x1, y1 = ogdf.bounding_box(ga)
    >>> round(x1 - x0) <= 760 and round(y1 - y0) <= 560
    True

The algorithm is normally a **class**, so your editor completes it and mypy
checks it. A string is accepted too, for when the choice comes from a config
file or a command line rather than from code.

This is a convenience over the classes, not a replacement: anything it does is
one documented call, and a workflow that needs to inspect or adjust the drawing
midway should use them directly.
"""

from __future__ import annotations

from typing import Any

from ogdf import _core
from ogdf._about import _capabilities
from ogdf._transforms import fit_to_box, normalize as _normalize, pack_components

__all__ = ["layout", "layout_names"]

# Short names for layouts whose class name does not reduce to something anyone
# would type. Everything else is resolved mechanically (see _resolve), so a
# newly bound layout is reachable by name without touching this table.
_EXTRA_ALIASES = {
    "stress": "StressMinimization",
    "kamada_kawai": "SpringEmbedderKK",
    "springkk": "SpringEmbedderKK",
    "mds": "PivotMDS",
    "mixer": "ModularMultilevelMixer",
    "planar": "PlanarStraightLayout",
    "arc": "LinearLayout",
}


def _by_name() -> dict[str, type]:
    """Every layout class, keyed by the names that resolve to it.

    Derived from the module's own exports rather than a hand-written list, so
    the table cannot fall behind the bindings: each class answers to its exact
    name, that name lowercased, and the name with a trailing "Layout" removed.
    """
    table: dict[str, type] = {}
    for name in _capabilities()["layouts"]:
        cls = getattr(_core, name)
        table[name] = cls
        table[name.lower()] = cls
        short = name[: -len("Layout")] if name.endswith("Layout") else name
        table.setdefault(short.lower(), cls)
    for alias, target in _EXTRA_ALIASES.items():
        if hasattr(_core, target):
            table[alias] = getattr(_core, target)
    return table


def layout_names() -> list[str]:
    """The names `layout()` accepts for its `algorithm`, sorted.

    Includes each layout's class name and its short aliases. Passing the class
    itself is preferred - it is checkable and completes in an editor - but these
    are what to use when the choice arrives as a string.
    """
    return sorted(_by_name())


def _resolve(algorithm: Any) -> tuple[Any, str]:
    """Return (layout instance, class name) for a class, instance, or name."""
    if isinstance(algorithm, str):
        table = _by_name()
        try:
            cls = table[algorithm]
        except KeyError:
            raise ValueError(
                f"unknown layout {algorithm!r}. Pass a layout class such as "
                f"ogdf.FMMMLayout, or one of: {', '.join(layout_names())}"
            ) from None
        return cls(), cls.__name__
    if isinstance(algorithm, type):
        return algorithm(), algorithm.__name__
    # An already-configured instance.
    if hasattr(algorithm, "call"):
        return algorithm, type(algorithm).__name__
    raise TypeError(
        f"algorithm must be a layout class, a layout instance, or a name; "
        f"got {algorithm!r}"
    )


def _apply(instance: Any, name: str, options: dict[str, Any]) -> None:
    """Apply `option=value` by calling the matching `set_option` setter.

    The mapping is mechanical, so it cannot drift from the bindings, and an
    unknown option reports what the layout does accept instead of failing
    obscurely.
    """
    for key, value in options.items():
        setter = getattr(instance, f"set_{key}", None)
        if setter is None:
            available = sorted(
                attribute[4:]
                for attribute in dir(instance)
                if attribute.startswith("set_")
            )
            raise TypeError(
                f"{name} has no option {key!r}. "
                + (
                    f"It accepts: {', '.join(available)}"
                    if available
                    else "It has no options."
                )
            )
        setter(value)


def layout(
    graph,
    algorithm: Any = None,
    *,
    attributes=None,
    seed: int | None = None,
    validate: bool = True,
    pack: bool = False,
    separation: float = 20.0,
    fit: tuple[float, float] | None = None,
    margin: float = 0.0,
    normalize: bool = False,
    **options: Any,
):
    """Lay out `graph` and return the resulting `GraphAttributes`.

    `algorithm` is a layout class (`ogdf.FMMMLayout`, the default), an
    already-configured layout instance, or one of `layout_names()`. Keyword
    options are forwarded to the layout's setters - `unit_edge_length=25.0`
    calls `set_unit_edge_length(25.0)` - and an unknown one raises `TypeError`
    listing what that layout accepts.

    The rest of the pipeline is opt-in:

    - `attributes` - lay out into an existing `GraphAttributes` (one you have
      already styled, say) instead of a fresh one with all attributes enabled.
    - `seed` - seed OGDF's random engine first, making a stochastic layout
      reproducible.
    - `validate` - check the layout's documented preconditions before running
      (on by default; the layout itself checks them regardless, this just fails
      before any work is done).
    - `pack` - spread disconnected components instead of leaving them piled.
    - `fit` - a `(width, height)` box to scale and centre the drawing into,
      with `margin` inside it.
    - `normalize` - move the lower-left corner to the origin. Ignored when
      `fit` is given, which already places the drawing.

    >>> import ogdf
    >>> g = ogdf.Graph()
    >>> with ogdf.seeded(1):
    ...     ogdf.random_planar_connected_graph(g, 30, 50)
    >>> ga = ogdf.layout(g, ogdf.FMMMLayout, unit_edge_length=25.0, seed=42)
    >>> ogdf.drawing_metrics(ga)["nodes"]
    30

    Metrics and provenance are each one further call - `ogdf.drawing_metrics(ga)`
    and `ogdf.provenance(...)` - and are deliberately not computed here, since
    the metrics are quadratic and most callers do not want them.
    """
    instance, name = _resolve(_core.FMMMLayout if algorithm is None else algorithm)
    _apply(instance, name, options)

    if validate and name in _core_operations():
        from ogdf._validate import check

        check(name, graph)

    if attributes is None:
        attributes = _core.GraphAttributes(graph, _core.ALL_ATTRIBUTES)
    if seed is not None:
        _core.seed_random_engine(int(seed))

    instance.call(attributes)

    if pack:
        pack_components(attributes, separation=separation)
    if fit is not None:
        width, height = fit
        fit_to_box(attributes, width, height, margin=margin)
    elif normalize:
        _normalize(attributes)
    return attributes


def _core_operations() -> tuple[str, ...]:
    from ogdf._validate import operations

    return operations()
