# Choosing a Layout

The package exposes nineteen layouts. Which one to use is decided almost
entirely by the *structure* of your graph, because most of them refuse - or
quietly mislead - on input they were not designed for. Start from the structure,
then narrow by scale and by what the drawing is for.

## Start here

| If your graph is ... | Use | Notes |
| --- | --- | --- |
| a tree or forest | `TreeLayout` | Classic layered tree; set the orientation. |
| a tree you want radially | `RadialTreeLayout` | Concentric levels; a single tree only. |
| a tree with heavy branching | `BalloonLayout` | Subtrees in enclosing circles; needs connectivity. |
| a DAG / has a natural flow | `SugiyamaLayout` | The workhorse for hierarchies. |
| a DAG you want strictly upward | `DominanceLayout`, `VisibilityLayout` | Every edge points up; no cycles allowed. |
| planar, and you want no crossings | `PlanarStraightLayout`, `FPPLayout`, `SchnyderLayout` | Straight-line grid drawings. |
| planar and triconnected | `TutteLayout` | Convex faces; the most regular planar result. |
| planar, drawn with boxes | `MixedModelLayout` | Orthogonal-ish routing, node boxes. |
| not planar but you want few crossings | `PlanarizationLayout` | Planarize, draw, then reinsert edges. |
| general, small to medium | `FMMMLayout` | The best default for an arbitrary graph. |
| general, large (10k+ nodes) | `MultilevelLayout` | Coarsens the graph first; handles disconnection. |
| general, and quality matters more than time | `StressMinimization` | Distances match graph distances well. |
| general, and speed matters most | `PivotMDS` | Fast approximate MDS. |
| dense, and you want structure visible | `CircularLayout` | Groups by connectivity around a circle. |
| to be read as an arc diagram | `LinearLayout` | Nodes on a line, edges as arcs. |

## By constraint

**Preconditions are enforced.** Every layout above with a structural
requirement checks it and raises `InvalidGraphError` rather than producing a
broken drawing. Ask first with `ogdf.validate("TutteLayout", g)` or
`ogdf.graph_report(g)` - see [Errors and preconditions](getting-started.md#errors-and-preconditions).

**Directedness.** OGDF stores every edge with a source and a target, but only
some layouts *read* the direction. `SugiyamaLayout`, `DominanceLayout`,
`VisibilityLayout`, and the tree layouts do; the force-directed, stress, planar,
and circular layouts do not. Set `attributes.directed = True` so the drawing
writers render arrowheads.

**Disconnected graphs.** `FMMMLayout`, `MultilevelLayout`, `SugiyamaLayout`
(with `set_arrange_ccs(True)`), and `TreeLayout` place components separately.
`SpringEmbedderKK` and `BalloonLayout` require a connected graph and say so.
`StressMinimization` needs `set_layout_components_separately(True)`.

**Multigraphs and self-loops.** The planar grid layouts require a *simple*
graph - no self-loops, no parallel edges - in the undirected sense. "Planar" for
a multigraph is decided on its underlying simple graph, so a graph that
`is_planar` reports as planar can still be rejected as non-simple. Check with
`ogdf.is_simple_undirected(g)` and `ogdf.has_self_loops(g)`.

**Scale.** Below a few thousand nodes, `FMMMLayout` is fast enough and looks
best. Above that, use `MultilevelLayout`. `StressMinimization` and
`SpringEmbedderKK` are quadratic-ish in practice and get slow first.

**Determinism.** The force-directed and multilevel layouts are randomized. Seed
them with `ogdf.seeded(n)` and record `ogdf.provenance()` - see
[Reproducibility](getting-started.md#reproducibility). The tree, planar, and
upward layouts are deterministic given a fixed graph and embedding.

## By output

- **Publication figures (SVG/TikZ).** Planar layouts and `SugiyamaLayout` give
  the most legible static drawings. Enable `ogdf.ALL_ATTRIBUTES` and set node
  sizes before laying out - most layouts respect node dimensions.
- **Notebook exploration.** `FMMMLayout` plus `ogdf.to_svg(ga)` renders inline
  with no temporary files.
- **Handing coordinates to another plotter.** Any layout, then
  `ogdf.to_networkx(g, ga)` for a `pos` dict - see
  [Python interoperability](getting-started.md#python-interoperability).

## Comparing candidates

When two layouts are plausible, measure instead of guessing. The heuristic
layouts report their achieved objective:

```python
import ogdf

g = ogdf.Graph()
ogdf.random_graph(g, 60, 120)

for name in ("SugiyamaLayout", "PlanarizationLayout"):
    with ogdf.seeded(1):
        ga = ogdf.GraphAttributes(g)
        layout = getattr(ogdf, name)()
        layout.call(ga)
        print(name, layout.number_of_crossings(),
              ga.bounding_box_width(), ga.bounding_box_height())
```

`ogdf.crossing_number(g, permutations=8)` gives a heuristic lower reference
point to compare those crossing counts against.
