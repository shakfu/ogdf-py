"""
ogdf - Python bindings for the Open Graph Drawing Framework (OGDF).

A curated subset covering graph construction, layout algorithms, core graph
algorithms, and file I/O. Everything is re-exported from the compiled `_core`
module (see `_core.pyi` for the typed API).

Example:
    >>> import ogdf
    >>> g = ogdf.Graph()
    >>> ogdf.random_planar_connected_graph(g, 20, 30)
    >>> ga = ogdf.GraphAttributes(g)
    >>> ogdf.FMMMLayout().call(ga)
    >>> ogdf.draw_svg(ga, "graph.svg")
    True

`ogdf.about()` (or `python -m ogdf`) reports the package and OGDF versions,
the platform, and the available capabilities - paste it into bug reports.
"""

from importlib import metadata as _metadata

from ogdf import _core
from ogdf._about import about, about_text
from ogdf._core import *  # noqa: F403
from ogdf._interop import (
    edge_array_to_dict,
    edge_array_to_list,
    edges_where,
    fill_edge_array,
    fill_node_array,
    from_edges,
    from_networkx,
    node_array_to_dict,
    node_array_to_list,
    nodes_where,
    to_edges,
    to_networkx,
)
from ogdf._layout import layout, layout_names
from ogdf._metrics import compare_layouts, drawing_metrics
from ogdf._random import (
    get_seed,
    new_seed,
    provenance,
    seeded,
    set_seed,
)
from ogdf._results import (
    STCut,
    ShortestPaths,
    min_st_cut,
    shortest_paths,
)
from ogdf._transforms import (
    center,
    fit_to_box,
    normalize,
    pack_components,
    scale,
    translate,
)
from ogdf._validate import (
    check,
    graph_report,
    is_valid_for,
    operations,
    requirements,
    validate,
)

__all__ = [name for name in dir(_core) if not name.startswith("_")]
__all__ += [
    "about",
    "about_text",
    "edge_array_to_dict",
    "edge_array_to_list",
    "edges_where",
    "fill_edge_array",
    "fill_node_array",
    "fit_to_box",
    "from_edges",
    "drawing_metrics",
    "from_networkx",
    "get_seed",
    "node_array_to_dict",
    "node_array_to_list",
    "new_seed",
    "normalize",
    "pack_components",
    "nodes_where",
    "min_st_cut",
    "provenance",
    "STCut",
    "ShortestPaths",
    "seeded",
    "scale",
    "set_seed",
    "shortest_paths",
    "to_edges",
    "translate",
    "to_networkx",
    "center",
    "check",
    "compare_layouts",
    "graph_report",
    "is_valid_for",
    "layout",
    "layout_names",
    "operations",
    "requirements",
    "validate",
]
# Single-sourced from pyproject.toml: the installed distribution metadata, or -
# if the metadata is unavailable - the version CMake compiled into the
# extension. Both derive from the same field, so they cannot disagree unless the
# extension is stale, which `tests/test_about.py` checks for.
try:
    __version__ = _metadata.version("ogdf-py")
except _metadata.PackageNotFoundError:  # pragma: no cover - source tree only
    __version__ = str(_core.build_info()["package_version"])
