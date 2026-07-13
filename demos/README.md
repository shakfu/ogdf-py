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
  FPP, planar-straight, planar-draw, mixed-model, circular, tree, radial tree,
  linear/arc, Tutte, dominance, visibility, multilevel, modular multilevel
  mixer, balloon, and orthogonal), one SVG per layout.
- **`styling_showcase.py`** - a wheel graph styled with per-degree node colors,
  ellipse shapes, sizes, labels, and edge arrows.
- **`algorithms_visual.py`** - visualizes algorithm results by coloring nodes
  and edges: connected / strongly-connected / biconnected components, a proper
  node coloring, Dijkstra and A* shortest paths, Bellman-Ford distances,
  topological numbering, a minimum spanning tree, minimum-cost flow, s-t minimum
  cut (with max flow), cut vertices and bridges, node/edge k-connectivity,
  triconnectivity (separation pair and SPQR summary), a maximum-weight matching,
  a minimum Steiner tree, the maximal planar subgraph, and crossing minimization
  (crossing number and edge-insertion routing).
- **`generators_zoo.py`** - builds a variety of named graphs (complete,
  bipartite, wheel, cube, grid, Petersen, trees, random regular) and draws each.
- **`io_roundtrip.py`** - writes a graph to GML, GraphML, DOT, GEXF, TLP, SVG,
  and TikZ, then reads each interchange format back and checks the topology
  round-trips.
- **`gallery.py`** - assembles all generated SVGs into a single self-contained
  `index.html` gallery (built automatically at the end of `make demos`; open
  `build/demo-output/index.html` to view every drawing side by side).

`_common.py` holds shared helpers (the output directory and color utilities).
