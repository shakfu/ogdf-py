# Getting Started

## Installation

### From PyPI

```bash
pip install ogdf-py
```

#### Support matrix

Binary wheels are published for these combinations; on anything else pip falls
back to the source distribution and builds OGDF at install time.

| Platform | Architectures | CPython |
| --- | --- | --- |
| Linux (manylinux, glibc) | x86_64, aarch64 | 3.10 - 3.14 |
| macOS | x86_64, arm64 | 3.10 - 3.14 |
| Windows | AMD64 | 3.10 - 3.14 |

Wheels are self-contained: OGDF is linked statically, so there is no runtime
dependency beyond the C++ standard library. Free-threaded builds, musl Linux,
PyPy, and 32-bit platforms are not covered by wheels and fall back to source.

#### Source-build requirements

The fallback builds OGDF itself, which is a native toolchain step rather than an
ordinary package install. It needs:

- `git` (unless the source is vendored - see below) and network access
- CMake >= 3.15
- a C++17 compiler (GCC, Clang, or MSVC Build Tools)
- roughly 2 GB of free disk space; expect 5-15 minutes on a typical machine,
  mostly spent compiling OGDF once

If a build fails, the bootstrap names the failing stage - source fetch, CMake
configuration, or compilation - and CMake reports which of the OGDF and COIN
static libraries is missing.

#### Offline and locked-down environments

The default source build clones OGDF during CMake configuration. Three
alternatives avoid that:

```bash
# 1. Vendor a source archive (no network at build time).
python scripts/bootstrap_ogdf.py --archive /path/to/ogdf-src.tar.gz

# 2. Copy an existing OGDF checkout.
python scripts/bootstrap_ogdf.py --source-dir /path/to/ogdf

# 3. Link against an OGDF you built separately.
pip install ogdf-py --config-settings=cmake.define.OGDF_PREBUILT_DIR=/path/to/ogdf
```

Set `OGDF_OFFLINE=1` to forbid the automatic clone outright: the build then
fails immediately with instructions instead of reaching for the network. The
equivalent environment variables are `OGDF_ARCHIVE`, `OGDF_SOURCE_DIR`, and
`OGDF_PREBUILT_DIR`; `OGDF_TAG` and `OGDF_REPO` override the pinned tag and
remote. A prebuilt tree must have been configured with
`-DOGDF_LIBRARY_TARGETS_ONLY=ON -DCMAKE_POSITION_INDEPENDENT_CODE=ON`.

The pinned OGDF tag lives in `scripts/ogdf-tag.txt`, which both the bootstrap
script and CMake read, so the tag reported by `ogdf.about()` always matches the
libraries that were linked in.

### From source

```bash
git clone https://github.com/shakfu/ogdf-py
cd ogdf-py
make bootstrap   # fetch OGDF at the pinned tag and build it from source (once)
uv sync          # build the extension
```

`make build` and `make sync` run the bootstrap automatically if OGDF has not been built yet. See `make help` for all targets.

## Checking the installation

`ogdf.about()` reports what is actually installed - package and OGDF versions,
the pinned OGDF tag, platform, compiler, and available capabilities. The same
report is printed by `python -m ogdf`:

```console
$ python -m ogdf
ogdf-py installation report

  package version    : 0.4.0
  OGDF version       : 2025.10 (pinned tag: foxglove-202510)
  OGDF system        : Unix/linux
  OGDF LP solver     : COIN-OR LP (Clp)
  OGDF memory manager: pool allocator (thread-safe)
  OGDF debug build   : False

  python             : CPython 3.13.11
  platform           : Linux-6.8.0-x86_64-with-glibc2.39 (x86_64)
  compiler           : GCC 13.3.0
  extension          : .../ogdf/_core.cpython-313-x86_64-linux-gnu.so

  capabilities       : 19 layouts, 99 algorithms/generators, 19 I/O functions, 27 types
```

Include this output in bug reports. `ogdf.about()` returns the same data as a
dict, with a `capability_names` key listing every exported name by category.

## Building graphs

```python
import ogdf

g = ogdf.Graph()
a, b, c = g.new_node(), g.new_node(), g.new_node()
g.new_edge(a, b)
g.new_edge(b, c)

print(g.number_of_nodes(), g.number_of_edges())   # 3 2
for node in g.nodes():
    print(node.index, node.degree)
```

Generators fill a graph directly:

```python
g = ogdf.Graph()
ogdf.complete_bipartite_graph(g, 3, 4)
```

## Layouts

Every layout writes coordinates into a `GraphAttributes`:

```python
ga = ogdf.GraphAttributes(g)
layout = ogdf.FMMMLayout()
layout.set_unit_edge_length(20.0)
layout.call(ga)
```

## Styling and drawing

Enable the styling attributes, then set colors, shapes, and arrows:

```python
ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
ogdf.SugiyamaLayout().call(ga)

for v in g.nodes():
    ga.set_fill_color(v, ogdf.Color(70, 110, 200))
    ga.set_shape(v, ogdf.Shape.ELLIPSE)

svg = ogdf.to_svg(ga)          # or ogdf.draw_svg(ga, "graph.svg")
tikz = ogdf.to_tikz(ga)        # LaTeX / PGF output
```

## Algorithms

Algorithms operate on the `Graph`. Those that produce per-node or per-edge results follow OGDF's idiom: you pass in an array to receive the output, and the function returns the scalar result.

```python
# Connected components -> count, plus a component id per node.
component = ogdf.NodeArrayInt(g)
n = ogdf.connected_components(g, component)

# Shortest paths from a source.
weight = ogdf.EdgeArrayDouble(g, 1.0)
dist = ogdf.NodeArrayDouble(g)
ogdf.dijkstra(g, weight, source, dist)

# Minimum spanning tree.
in_tree = ogdf.EdgeArrayBool(g)
total = ogdf.min_spanning_tree(g, weight, in_tree)
```

## Reproducibility

The random generators, the force-directed and multilevel layouts, and the
randomized restarts inside `crossing_number` and `PlanarizationLayout` are all
stochastic. OGDF draws that randomness from a single process-wide engine, so
seeding is a global operation rather than a per-call argument:

```python
with ogdf.seeded(20260831):
    g = ogdf.Graph()
    ogdf.random_graph(g, 30, 60)
    ga = ogdf.GraphAttributes(g)
    ogdf.FMMMLayout().call(ga)
```

`ogdf.set_seed(n)` seeds without a block, `ogdf.get_seed()` reports the seed
last set (`None` if never), and `ogdf.new_seed()` draws a fresh value to record
and reuse. On exit `seeded()` re-applies the previous *seed*; the engine cannot
report its stream position, so this restores the sequence that followed that
earlier seed rather than resuming exactly where the block began.

`FMMMLayout.set_rand_seed()` additionally seeds that layout's own engine.

### What is guaranteed

Given the same seed, the same package version, and the same OGDF build, a
sequence of calls produces the same graph and the same coordinates. Results are
**not** guaranteed bit-for-bit across platforms, compilers, or OGDF versions -
layout code is floating-point heavy and sensitive to instruction selection and
library math.

Record `ogdf.provenance()` next to a result so a later run can be compared
against like conditions:

```python
>>> ogdf.set_seed(42)
>>> ogdf.provenance(algorithm="FMMMLayout", unit_edge_length=20.0)
{'seed': 42, 'package_version': '0.4.0', 'ogdf_version': '2025.10',
 'ogdf_tag': 'foxglove-202510', 'platform': '...', 'machine': 'x86_64',
 'python_version': '3.13.11',
 'settings': {'algorithm': 'FMMMLayout', 'unit_edge_length': 20.0}}
```

The result is JSON-serializable as long as the settings you pass are.

### Heuristic results

Algorithms that optimize heuristically report what they actually achieved, so
runs and seeds can be compared numerically rather than by eye:

```python
layout = ogdf.PlanarizationLayout()
layout.call(ga)
layout.number_of_crossings()      # the achieved objective, not a proven minimum

sugiyama = ogdf.SugiyamaLayout()
sugiyama.call(ga)
sugiyama.number_of_crossings(), sugiyama.number_of_levels()

ogdf.crossing_number(g, permutations=8)   # heuristic minimum, more restarts
```

## Python interoperability

OGDF's `Node`/`Edge` handles and `NodeArray`/`EdgeArray` containers are exact
but foreign. These helpers bridge them to the data you already have.

### Edge lists

```python
g, mapping = ogdf.from_edges([("a", "b"), ("b", "c"), ("c", "a")])
keys = {v: k for k, v in mapping.items()}      # the inverse mapping
ogdf.to_edges(g, keys=keys)                    # [('a', 'b'), ('b', 'c'), ('c', 'a')]
```

`mapping` takes each of your keys to its `Node`; `nodes=` adds isolated nodes.
Extra entries in each tuple are ignored, so a weighted `(u, v, w)` edge list
works unchanged. Repeated pairs become parallel edges - OGDF is a multigraph
model - and self-loops are preserved.

### NetworkX

```python
import networkx as nx

h = nx.les_miserables_graph()
g, ga, mapping = ogdf.from_networkx(h, graph_attributes=True,
                                    label_attribute="__node__")
ogdf.FMMMLayout().call(ga)
ogdf.draw_svg(ga, "lesmis.svg")
```

All four NetworkX classes are handled. A directed input produces one OGDF edge
per directed edge and sets `attributes.directed`; a multigraph produces one edge
per parallel edge, so counts are preserved. `label_attribute` copies a NetworkX
node attribute into the node labels (`"__node__"` uses the node object itself).

Going the other way, `to_networkx` picks a lossless class by default - directed
when the attributes say so, a multigraph when the graph has parallel edges or
self-loops - and copies the layout back:

```python
h = ogdf.to_networkx(g, ga)
pos = {n: (d["x"], d["y"]) for n, d in h.nodes(data=True)}
nx.draw(h, pos)
```

NetworkX is an optional dependency; importing it is deferred until one of these
two functions is called.

### Arrays and results

Node and edge attributes are not carried automatically - OGDF has no general
attribute store - but node identity is, so any attribute transfers through the
mapping:

```python
weight = ogdf.EdgeArrayDouble(g, 1.0)
ogdf.fill_edge_array(weight, {0: 2.5, 1: 0.5}, g)      # keyed by edge.index
ogdf.edge_array_to_dict(weight, g)                     # back out again
ogdf.node_array_to_list(dist, g)                       # in node iteration order
```

`fill_node_array` / `fill_edge_array` accept either a mapping (nodes missing
from it keep their current value) or a sequence in iteration order.

Results that OGDF reports as a boolean array become ordinary Python lists:

```python
in_tree = ogdf.EdgeArrayBool(g)
ogdf.min_spanning_tree(g, weight, in_tree)
tree_edges = ogdf.edges_where(in_tree, g)     # a list of Edge
```

`nodes_where` is the node-side equivalent, used for cuts, matchings, and
independent sets.

## Result objects

The array convention is efficient but lossy: `dijkstra` builds a shortest-path
tree internally and throws it away, so you get distances but no paths. For the
algorithms where that matters, a second entry point keeps the work and returns
it with named fields. Both forms remain available - use the array form when
calling in bulk.

### Shortest paths

```python
paths = ogdf.shortest_paths(g, source, weight)   # weight optional (unit edges)

paths.distance(v)            # math.inf if unreachable, not a magic sentinel
paths.path_to(v)             # list of Edge, [] for the source, None if unreachable
paths.nodes_to(v)            # list of Node including both endpoints
paths.predecessor_edge(v)    # the edge used to reach v
paths.reachable(v)           # also: `v in paths`
paths.unreachable_nodes()
paths.distances(keys=keys)   # dict, keyed by node.index or your own keys
```

`algorithm` defaults to `"auto"`: Dijkstra, unless `weight` is an
`EdgeArrayInt` containing a negative length, in which case Bellman-Ford. Force
either with `algorithm="dijkstra"` / `"bellman_ford"`. A reachable negative
cycle raises `AlgorithmError` rather than returning meaningless distances.

!!! note "Why Bellman-Ford takes integers"
    `dijkstra` and `a_star_search` take `EdgeArrayDouble`; `bellman_ford` takes
    `EdgeArrayInt`. That asymmetry is OGDF's: its shortest-path module interface
    is defined over `int`, and it ships no floating-point Bellman-Ford. Since
    the two algorithms are never interchangeable anyway - Dijkstra cannot accept
    the negative weights that are Bellman-Ford's whole purpose - the binding
    reports the constraint rather than papering over it with a reimplementation.
    `shortest_paths` will accept an `EdgeArrayInt` for Dijkstra and convert it.

### Cuts

```python
cut = ogdf.min_st_cut(g, weight, source, sink)   # directed=True by default

cut.value          # equals the max flow, by duality
cut.edges          # the edges crossing the cut
value, edges = cut # STCut is a NamedTuple, so it still unpacks as a pair
```

A minimum cut need not be unique - the diamond `s->a, s->b, a->t, b->t, a->b`
at unit capacity has two, `({s}, {a,b,t})` and `({s,a,b}, {t})`, both of value
2 - and which one you get is OGDF's choice.

!!! warning "There is no node partition, deliberately"
    `MinSTCutMaxFlow` exposes a *front* and a *back* cut, which look like the
    two sides of the cut but are not. They are the extreme cuts nearest the
    source and nearest the sink; when the minimum cut is not unique these are
    **different cuts**, and neither is guaranteed to match the edges you were
    given. On the complete digraph on 20 nodes the front cut is `{s}` while the
    returned edges are the sink's in-edges - so reporting the two together
    would describe no single cut.

    If you need the partition, derive it from the edges: the source side is
    what stays reachable from `source` once they are removed. That is
    guaranteed to be consistent with the cut you actually got.

`max_flow` keeps its array form and reports the flow value only - OGDF's
max-flow module computes no cut. Use `min_st_cut` for the partition induced by
the flow; by max-flow min-cut duality the values agree.

### What every result promises

- **Ordering.** Lists come back in the graph's node or edge iteration order,
  which is insertion order until something is deleted.
- **Unreachable.** `shortest_paths` reports `math.inf` and `None`. The raw array
  functions leave OGDF's sentinel in place, documented per function.
- **Parallel edges.** Honoured individually - the cheapest of a parallel bundle
  wins, and each carries flow separately.
- **Directedness.** Stated per function. `dijkstra` and the unweighted BFS treat
  edges as undirected unless told otherwise; `bellman_ford` always honours
  direction; the matching and spanning-tree routines ignore it.
- **Provenance.** Every algorithm docstring says whether it is exact, heuristic,
  or approximate - `node_coloring` is a heuristic upper bound, `steiner_tree` is
  a 2-approximation, `maximal_matching` is maximal but not maximum.

### Node identity

Conversions are keyed by whatever hashable object you use on the Python side,
and default to `node.index` when you do not supply a mapping. An index is stable
for as long as the node exists, but OGDF reuses indices after deletion, so a
mapping captured before a mutation must not be reused afterwards.

## One call: `layout()`

Everything above is a separate step because sometimes you need to interleave
them. When you do not, `layout()` is the whole sequence at once:

```python
ga = ogdf.layout(g, ogdf.FMMMLayout, unit_edge_length=25.0,
                 seed=42, pack=True, fit=(800, 600), margin=20)
ogdf.draw_svg(ga, "graph.svg")
```

The algorithm is normally a **class**, so your editor completes it and mypy
checks it. Keyword options are forwarded to that layout's setters -
`unit_edge_length=25.0` calls `set_unit_edge_length(25.0)` - and an unknown one
tells you what the layout does accept:

```pycon
>>> ogdf.layout(g, ogdf.FMMMLayout, bogus=1)
TypeError: FMMMLayout has no option 'bogus'. It accepts: fixed_iterations,
new_initial_placement, quality_versus_speed, rand_seed, unit_edge_length,
use_high_level_options
```

A string works too, for when the choice comes from a config file or a command
line rather than from code. `ogdf.layout_names()` lists what is accepted -
every class name plus short aliases like `"fmmm"`, `"stress"`, `"planar"`:

```python
ga = ogdf.layout(g, "sugiyama", runs=8, transpose=True)
```

The optional steps are all off by default: `seed` for reproducibility,
`validate` (on) to check preconditions before doing any work, `pack` to spread
disconnected components, `fit`/`margin` to place the drawing in a box,
`normalize` to move the corner to the origin, and `attributes` to lay out into
a `GraphAttributes` you have already styled.

It returns the `GraphAttributes`, ready to draw. Metrics and provenance are
deliberately not computed for you - `ogdf.drawing_metrics(ga)` is quadratic and
most callers do not want it - but each is one further call.

## Errors and preconditions

Many OGDF algorithms have structural preconditions - a tree, a planar graph, a
DAG. OGDF documents them but compiles its assertions out of a release build, so
violating one is undefined behaviour. The bindings check every documented
precondition before entering OGDF and raise a typed exception instead:

```python
import ogdf

g = ogdf.Graph()
ogdf.complete_graph(g, 5)          # K5 is not planar
ogdf.SchnyderLayout().call(ogdf.GraphAttributes(g))
# ogdf.InvalidGraphError: SchnyderLayout requires a planar graph
```

The exception hierarchy is:

```text
Exception
 +-- OGDFError                     everything the bindings raise deliberately
      +-- PreconditionError        (also ValueError) a documented precondition is unmet
      |    +-- InvalidGraphError   the graph has the wrong structure
      +-- UnsupportedFormatError   (also ValueError) the format cannot do this
      +-- AlgorithmError           (also RuntimeError) the algorithm found no result
```

The mix-ins mean `except ValueError` and `except RuntimeError` keep working.

Besides graph structure, the bindings reject arrays that belong to a different
graph than the one passed in, `None` node arguments, negative weights where the
algorithm assumes non-negative ones (`dijkstra`, `a_star_search`, `max_flow`,
`min_cut`, `min_st_cut`, `steiner_tree`), and a source equal to its sink.

### Asking before you call

To check an input without triggering the exception:

```python
ogdf.requirements("TutteLayout")   # ('at least 3 nodes', 'planar', 'triconnected')
ogdf.validate("TutteLayout", g)    # ['planar']  - the unmet ones, in check order
ogdf.is_valid_for("TutteLayout", g)  # False
ogdf.check("TutteLayout", g)       # raises InvalidGraphError, runs nothing else
ogdf.operations()                  # every operation with recorded preconditions
```

`ogdf.graph_report(g)` describes a graph against the whole requirement
vocabulary at once - node and edge counts plus simplicity, connectivity,
biconnectivity, triconnectivity, planarity, whether a planar embedding is in
place, acyclicity, tree/forest, and bipartiteness:

```python
>>> ogdf.graph_report(g)
{'nodes': 5, 'edges': 10, 'non_empty': True, ..., 'planar': False, ...}
```

The table behind `requirements()` mirrors the checks compiled into the
bindings, so an empty `validate()` and a call that is not rejected for
structural reasons mean the same thing.

## File I/O

```python
ogdf.write_gml(ga, "graph.gml")
ogdf.write_graphml(ga, "graph.graphml")

g2 = ogdf.Graph()
ga2 = ogdf.GraphAttributes(g2, ogdf.ALL_ATTRIBUTES)
ogdf.read_gml(ga2, g2, "graph.gml")
```

The generic `write(ga, filename)` chooses the format from the extension; it raises `ValueError` for formats that cannot store attributes.

## Demos

```bash
make demos
```

This writes example drawings and data files to `build/demo-output/` and builds a self-contained `index.html` gallery.
