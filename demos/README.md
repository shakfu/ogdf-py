# Demos

Illustrative scripts that exercise the `ogdf` bindings. Each writes its output
(SVG drawings and a few data files) to `build/demo-output/`.

## Running

```bash
make demos                      # run every demo
uv run python demos/run_all.py  # equivalent
```

Each demo is also runnable on its own, e.g.:

```bash
uv run python demos/layouts_gallery.py
```

## What each demo does

- **`layouts_gallery.py`** - renders graphs with every layout algorithm
  (Sugiyama, FMMM, GEM, Kamada-Kawai, stress minimization, pivot MDS, Schnyder,
  circular, tree, radial tree, linear/arc, Tutte, dominance, visibility, and
  orthogonal), one SVG per layout.
- **`styling_showcase.py`** - a wheel graph styled with per-degree node colors,
  ellipse shapes, sizes, labels, and edge arrows.
- **`algorithms_visual.py`** - visualizes algorithm results by coloring:
  connected components, a proper node coloring, shortest-path distances (as a
  gradient), a minimum spanning tree, cut vertices and bridges, a maximum-weight
  matching, Bellman-Ford distances, a minimum-cost flow (edge width by flow),
  and a minimum Steiner tree.
- **`generators_zoo.py`** - builds a variety of named graphs (complete,
  bipartite, wheel, cube, grid, Petersen, trees, random regular) and draws each.
- **`io_roundtrip.py`** - writes a graph to GML, GraphML, DOT, GEXF, TLP, SVG,
  and TikZ, then reads each interchange format back and checks the topology
  round-trips.
- **`gallery.py`** - assembles all generated SVGs into a single self-contained
  `index.html` gallery (built automatically at the end of `make demos`; open
  `build/demo-output/index.html` to view every drawing side by side).

`_common.py` holds shared helpers (the output directory and color utilities).
