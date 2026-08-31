# Drawing Quality Metrics

A layout is easy to admire and hard to judge. These metrics turn a drawing into
numbers you can rank, regression-test, and put in a table.

They measure the **drawing**, not the graph, so they depend on the
`GraphAttributes` you pass. Run a layout first.

## Everything at once

```python
import ogdf

g = ogdf.Graph()
with ogdf.seeded(1):
    ogdf.random_graph(g, 40, 80)
ga = ogdf.GraphAttributes(g)
ogdf.FMMMLayout().call(ga)

ogdf.drawing_metrics(ga)
```

```python
{'nodes': 40, 'edges': 80,
 'crossings': 104,
 'edge_length_min': 0.0, 'edge_length_max': 67.268,
 'edge_length_mean': 47.128, 'edge_length_stdev': 12.142, 'edge_length_cv': 0.258,
 'width': 224.0, 'height': 223.0, 'area': 49952.0, 'aspect_ratio': 1.004,
 'node_overlap_pairs': 11, 'node_overlap_area': 820.0,
 'min_angle': 0.0, 'min_angle_degrees': 0.0,
 'stress': 82.502}
```

That `edge_length_min` of 0 and `min_angle` of 0 are not bugs - see
[Reading the degenerate cases](#reading-the-degenerate-cases) below.

A plain dict of plain numbers, so it serializes directly and sits happily next
to `ogdf.provenance()` in a benchmark row.

## What each one means

| Metric | Reading | Better |
| --- | --- | --- |
| `crossings` | Edge crossings in the drawing, bends included | lower |
| `edge_length_cv` | Standard deviation over mean length - how uneven the edges are, independent of scale | lower (0 = uniform) |
| `area` | Extent of the drawing, node boxes and bends included | context |
| `aspect_ratio` | Longer side over shorter, so always `>= 1` | near 1 for a page |
| `node_overlap_pairs` | Node boxes that collide. Always 0 if you never set node sizes | 0 |
| `min_angle` | Angular resolution in radians: the tightest angle between two edges at a node | higher |
| `stress` | Scale-normalized deviation of drawn distances from graph hop distances | lower (0 = perfect) |

The individual functions are also available: `count_crossings`, `edge_lengths`
(the full distribution, in edge order), `bounding_box`, `node_overlaps`,
`min_angle`, and `stress`.

## Comparing layouts

```python
rows = ogdf.compare_layouts(g, {
    "sugiyama": ogdf.SugiyamaLayout,
    "fmmm": ogdf.FMMMLayout,
    "stress": ogdf.StressMinimization,
}, seed=1)
```

Each entry gets a fresh `GraphAttributes`, so runs cannot contaminate one
another, and `seed` makes the randomized layouts comparable like for like.
Results come back best-first by crossings then stress. A layout whose
preconditions the graph fails is reported with an `error` key and sorted last
rather than raising - the usual reason to compare layouts is that you do not
yet know which apply.

Pass a zero-argument factory instead of a class when you want to configure it:

```python
def tuned():
    layout = ogdf.FMMMLayout()
    layout.set_unit_edge_length(50.0)
    return layout

ogdf.compare_layouts(g, {"tuned": tuned, "default": ogdf.FMMMLayout}, seed=1)
```

## Placing the drawing

The metrics tell you a drawing does not fit its target; the transforms do
something about it. All of them mutate the `GraphAttributes` in place, and all
of them move edge bend points along with node coordinates - so a routed drawing
survives intact.

```python
ogdf.normalize(ga)                    # lower-left corner to (0, 0)
ogdf.center(ga, x=0, y=0)             # bounding box centred on a point
ogdf.translate(ga, dx, dy)
ogdf.scale(ga, 2.0, about="center")   # or "origin", "min", or an (x, y) point
ogdf.fit_to_box(ga, 800, 600, margin=20)
ogdf.pack_components(ga, separation=30)
```

**`scale` leaves node sizes alone by default.** Scaling up is usually how you
separate overlapping nodes, and growing the boxes too would defeat that. Pass
`scale_node_sizes=True` to scale the whole picture.

**`fit_to_box` preserves aspect ratio**, fitting to whichever axis binds first
and centring in the other, and returns the factor it applied. It scales node
sizes by default so the fit is exact. With `scale_node_sizes=False` the node
boxes keep their size while the layout shrinks around them - the factor is
solved for rather than estimated, so the fit is still exact, and a box too small
to hold the nodes at their fixed size returns `0.0`.

**`pack_components` fixes the pile.** Several layouts place every connected
component at the same origin, so a disconnected graph comes back stacked. This
tiles them with OGDF's packer and returns the component count; a connected graph
is untouched.

The usual pipeline for getting a graph onto a page:

```python
ogdf.FMMMLayout().call(ga)
ogdf.pack_components(ga, separation=30)     # spread disconnected pieces
ogdf.fit_to_box(ga, 1000, 800, margin=20)   # then fit the whole thing
ogdf.draw_svg(ga, "graph.svg")
```

Measure before and after with `drawing_metrics(ga)` - `area`, `aspect_ratio`,
and `node_overlap_pairs` are the ones these move.

## Reading the degenerate cases

Two metrics collapse easily, and a real drawing usually contains something that
collapses them. Read them with that in mind.

**Self-loops have length 0.** A straight-line drawing gives a self-loop no
extent, so it contributes 0 to the length distribution and drags
`edge_length_min` to 0 and the mean down. `random_graph` produces self-loops, so
this shows up quickly. `ogdf.has_self_loops(g)` tells you whether to expect it;
filter them out of `edge_lengths(ga)` if you want the distribution over drawn
edges only.

**`min_angle` is a worst case, not an average.** A single pair of exactly
collinear edges at one node sends it to 0 and hides everything else. This is
common, because several layouts round coordinates to integers and collinear
triples then appear by accident. A 0 here means "somewhere in this drawing two
edges overlap", which is worth knowing, but it does not rank two otherwise
different layouts.

**Stress is not normalized by graph size.** It is a sum over node pairs, so it
grows with the graph. Compare stress between layouts *of the same graph* - that
is what `compare_layouts` does - and do not compare it across graphs.

## Things worth knowing

**Crossings measure the drawing, not the graph.** `count_crossings(ga)` counts
what was actually drawn; `crossing_number(g)` is a heuristic minimum over all
drawings. The first can never be below the second, and the gap is how much your
layout is leaving on the table.

**Two edges meeting at a node do not cross there**, but an endpoint touching
another edge's interior does count. Collinear overlapping edges - parallel edges
drawn straight, say - are not counted at all, since they coincide rather than
cross.

**Stress is scale-normalized by default.** A drawing can be scaled arbitrarily
without getting better, so `stress` first rescales by the factor that minimizes
the sum. That is what makes it comparable across layouts working at different
scales. Pass `normalize=False` for the raw sum. Disconnected pairs have no hop
distance and are skipped.

**Node overlap needs node sizes.** Nodes are axis-aligned boxes of their width
and height. If you never set them, every node is a point and nothing overlaps.

**These are quadratic.** Crossings in the number of edges, overlap and stress in
the number of nodes. That is fine for the thousands-of-nodes drawings people
actually inspect; it is not something to call in a hot loop.
