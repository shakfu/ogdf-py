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
"""

from ogdf import _core
from ogdf._core import *  # noqa: F403

__all__ = [name for name in dir(_core) if not name.startswith("_")]
__version__ = "0.1.1"
