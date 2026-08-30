# Recipes

Four complete workflows, each runnable end to end. Every one is exercised by
the test suite (`tests/test_recipes.py`), so they stay correct.

## 1. NetworkX to SVG

Take a graph you already have in NetworkX, lay it out with OGDF, and write a
styled SVG.

```python
import networkx as nx
import ogdf

h = nx.les_miserables_graph()

# Node identity is preserved through `mapping`; the label attribute carries the
# NetworkX node names into the drawing.
g, ga, mapping = ogdf.from_networkx(
    h, graph_attributes=True, label_attribute="__node__"
)

# Size nodes by degree before laying out - layouts respect node dimensions.
for key, v in mapping.items():
    radius = 8.0 + 2.0 * h.degree(key)
    ga.set_width(v, radius)
    ga.set_height(v, radius)

with ogdf.seeded(20260831):
    layout = ogdf.FMMMLayout()
    layout.set_unit_edge_length(30.0)
    layout.call(ga)
    # Record the provenance inside the block: on exit `seeded` restores the
    # previous seed, so `ogdf.get_seed()` no longer reports this one.
    provenance = ogdf.provenance(algorithm="FMMMLayout", unit_edge_length=30.0)

ogdf.draw_svg(ga, "lesmis.svg")
```

`ogdf.to_svg(ga)` returns the same SVG as a string, which is what to use in a
notebook (`IPython.display.SVG(ogdf.to_svg(ga))`).

To go back the other way and plot with NetworkX instead:

```python
back = ogdf.to_networkx(g, ga)
pos = {n: (d["x"], d["y"]) for n, d in back.nodes(data=True)}
nx.draw(back, pos, node_size=20)
```

## 2. DAG to a layered SVG

A dependency graph, drawn top-to-bottom with arrowheads.

```python
import ogdf

dependencies = [
    ("app", "http"), ("app", "db"), ("http", "tls"),
    ("http", "sockets"), ("db", "sockets"), ("tls", "crypto"),
]

g, mapping = ogdf.from_edges(dependencies)

# Fail early and explicitly if the "DAG" turns out to have a cycle.
ogdf.check("topological_numbering", g)

ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
ga.directed = True
for key, v in mapping.items():
    ga.set_node_label(v, key)
    ga.set_width(v, 60.0)
    ga.set_height(v, 24.0)
    ga.set_fill_color(v, ogdf.Color(235, 240, 250))
for e in g.edges():
    ga.set_arrow(e, ogdf.EdgeArrow.LAST)

layout = ogdf.SugiyamaLayout()
layout.set_arrange_ccs(True)
layout.call(ga)
print("crossings:", layout.number_of_crossings(),
      "levels:", layout.number_of_levels())

ogdf.draw_svg(ga, "dependencies.svg")
```

The build order comes from the same graph. An edge points from a component to
what it depends on, so a valid build order is the *reverse* topological
numbering - dependencies first:

```python
order = ogdf.NodeArrayInt(g)
ogdf.topological_numbering(g, order)
keys = {v: k for k, v in mapping.items()}
build_order = sorted(g.nodes(), key=lambda v: order[v], reverse=True)
print([keys[v] for v in build_order])
# ['crypto', 'sockets', 'tls', 'db', 'http', 'app']
```

## 3. Planar graph to TikZ

A crossing-free drawing for a LaTeX document.

```python
import ogdf

g = ogdf.Graph()
with ogdf.seeded(7):
    ogdf.random_planar_triconnected_graph(g, 24, 48)

# TutteLayout gives the most regular planar drawing, but needs triconnectivity.
# Fall back to a straight-line grid layout otherwise.
if ogdf.is_valid_for("TutteLayout", g):
    layout = ogdf.TutteLayout()
else:
    layout = ogdf.PlanarStraightLayout()

ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
for v in g.nodes():
    ga.set_width(v, 10.0)
    ga.set_height(v, 10.0)
    ga.set_fill_color(v, ogdf.Color(70, 110, 200))
layout.call(ga)

with open("planar.tex", "w") as f:
    f.write(ogdf.to_tikz(ga))
```

Verify the promise rather than trusting it - a planar graph drawn by a planar
layout should have no crossings at all:

```python
assert ogdf.crossing_number(g) == 0
```

## 4. Weighted graph to an annotated drawing

Compute a result, then render it. Here: a minimum spanning tree, highlighted on
top of the full graph.

```python
import ogdf

g, mapping = ogdf.from_edges(
    [("a", "b", 4), ("b", "c", 1), ("c", "d", 3),
     ("d", "a", 2), ("a", "c", 5), ("b", "d", 6)]
)
keys = {v: k for k, v in mapping.items()}

# Move the weights from the Python edge list into an EdgeArray.
weight = ogdf.EdgeArrayDouble(g, 1.0)
ogdf.fill_edge_array(weight, [4, 1, 3, 2, 5, 6], g)

in_tree = ogdf.EdgeArrayBool(g)
total = ogdf.min_spanning_tree(g, weight, in_tree)

# The result as an ordinary Python list, no array plumbing.
tree_edges = ogdf.edges_where(in_tree, g)
print(total, [(keys[e.source], keys[e.target]) for e in tree_edges])

ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
for key, v in mapping.items():
    ga.set_node_label(v, key)
    ga.set_width(v, 24.0)
    ga.set_height(v, 24.0)
for e in g.edges():
    ga.set_edge_label(e, str(int(weight[e])))
    if in_tree[e]:
        ga.set_edge_stroke_color(e, ogdf.Color(200, 60, 60))
        ga.set_edge_stroke_width(e, 3.0)
    else:
        ga.set_edge_stroke_color(e, ogdf.Color(200, 200, 200))

ogdf.FMMMLayout().call(ga)
ogdf.draw_svg(ga, "mst.svg")
```

The same shape works for any array-valued result: run the algorithm, turn the
array into a list with `ogdf.edges_where` / `ogdf.nodes_where`, and style from
it.
