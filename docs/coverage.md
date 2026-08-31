# Coverage

This page tracks what OGDF functionality is exposed by `ogdf-py`. It is a living checklist: `ogdf-py` is a **curated subset**, so most of OGDF is intentionally excluded.

**Legend:** `[x]` = bound and available in Python, `[ ]` = not (yet) bound. Unbound items scheduled for the next additions may be tagged `**(priority)**`; see the [Priority roadmap](#priority-roadmap).

Most of this page tracks OGDF functionality. The [Python layer](#python-layer) section at the end covers the parts of the API that are *not* a binding of anything - diagnostics, the exception taxonomy, interoperability, and reproducibility - which exist because a faithful binding alone is not a usable Python package.

**Scope rationale.** The binding targets OGDF's genuine differentiators for Python users - **graph drawing** and **planarity** - plus a **core set of common graph algorithms** (even where these overlap networkx/scipy) for a self-contained experience. Because that common-algorithm core is explicitly in scope, canonical routines users reach for next to what is already bound - notably **A\*** (alongside `dijkstra`/`bellman_ford`) - are treated as in-scope gaps to close, not as exotic exclusions. That said, the core covers algorithms OGDF actually implements well: **PageRank** is intentionally omitted because OGDF only ships an undirected, [0, 1]-normalized variant that is degree-dominated and not the canonical directed measure (see below). Genuinely exotic or specialized algorithms, and large subsystems (clustering, UML, hypergraphs, cluster planarity, SEFE), are excluded unless there is concrete demand. Contributions that move an item from `[ ]` to `[x]` are welcome.

## Priority roadmap

Highest-value gaps given the drawing + planarity focus and the common-algorithm core. Tiers 1 through 3 are complete. Future priorities are tagged `**(priority)**` in the sections below.

**Done (Tier 1):**

1. **Planar straight-line grid layouts** - `FPPLayout`, `PlanarStraightLayout`, `PlanarDrawLayout`, `MixedModelLayout`, completing the planar-drawing family alongside `SchnyderLayout`.

2. **Common shortest-path gap** - `a_star_search`. (PageRank was evaluated and dropped: OGDF's `BasicPageRank` is undirected and [0, 1]-normalized, so it is degree-dominated and not canonical directed PageRank - little unique value over `node.degree`. Directed PageRank is left to networkx/igraph rather than hand-rolled here.)

3. **Crossing number** - `crossing_number`, the heuristic minimum computed by the subgraph planarizer, now a standalone call rather than a hidden step in `PlanarizationLayout`.

**Done (Tier 2):**

4. **s-t min cut** (`min_st_cut`, directed or undirected) and **k-connectivity** (`node_connectivity`, `edge_connectivity`, global and local) - completing the flow/cut and connectivity families that were only partially bound.

**Done (Tier 2, follow-on):**

5. **Edge-insertion routing** (`insert_edges`) - routes a chosen set of edges through the rest of the graph (which must be planar once they are removed) and returns, per edge, the original edges it crosses. Uses the variable-embedding inserter with no remove-reinsert, so crossings are attributed cleanly to the inserted edges rather than re-routed across the whole drawing.

**Done (Tier 3 - ergonomics and operational trust):**

6. **Install confidence** - `about()` / `python -m ogdf`, offline and prebuilt-OGDF build paths, a documented support matrix, and stage-specific build failures.

7. **Errors and preconditions** - an exception taxonomy (`OGDFError` and friends), enforcement of every documented precondition, and `validate()` / `graph_report()` helpers.

8. **Python interoperability** - NetworkX and edge-list conversion, array-to-container helpers, and results as ordinary Python collections.

9. **Reproducibility** - seeding for every stochastic operation, `provenance()` metadata, and achieved objective values from the heuristic layouts.

**Done (Tier 4 - results, placement, and measurement):**

10. **Result objects** - `shortest_paths()` returns distances *and* the shortest-path tree that the array form discards, so paths, predecessors, and reachability are available without rebuilding them; `min_st_cut()` returns an `STCut` with named fields. The array-output functions are unchanged and remain the bulk-calling path. Every algorithm docstring now states its provenance (exact / heuristic / approximate), its directedness, its parallel-edge behaviour, and its unreachable sentinel.

    The node partition for `min_st_cut` was investigated and **deliberately not exposed**. OGDF's front and back cuts are the extreme minimum cuts nearest the source and nearest the sink; when the minimum cut is not unique they are different cuts, and neither reliably corresponds to the edge list returned alongside them. Callers who need the partition should derive it from the cut edges.

    The `int` / `double` split between `bellman_ford` and `dijkstra` is **kept and documented** rather than removed: OGDF's `ShortestPathModule` interface is defined over `int` and it ships no floating-point Bellman-Ford, so closing the gap would mean reimplementing the algorithm rather than binding one. The two are not interchangeable anyway - Dijkstra rejects the negative weights Bellman-Ford exists for. `shortest_paths()` accepts either array type and picks the engine.

11. **Drawing quality metrics** - `count_crossings`, `edge_lengths`, `bounding_box`, `node_overlaps`, `min_angle`, and `stress`, aggregated by `drawing_metrics()` and ranked by `compare_layouts()`. Computed over the drawn polylines, so edge bends count.

12. **Coordinate transforms** - `normalize`, `center`, `translate`, `scale`, `fit_to_box`, and `pack_components` (binding OGDF's `TileToRowsCCPacker`). All move edge bends as well as node coordinates, so routed drawings survive.

13. **High-level `layout()` facade** - one call from graph to placed drawing, composing preconditions, seeding, the layout, component packing, and fit-to-box. The algorithm is a class by default so it stays type-checked and completable; a string is accepted for config-driven use, and options are forwarded to the layout's setters by a mechanical `set_X` mapping that cannot drift from the bindings.

**Not scheduled:**

- Planarity depth: combinatorial embedding + dual graph, upward planarity testing, planar separators.

- A high-level layout facade (`layout(graph, algorithm=...)` returning a result object). Worth doing only after item 10 settles the shape of a result, or it would be built twice.

## Graph model and attributes

- [x] `Graph`, `Node`, `Edge`, node/edge iteration

- [x] `NodeArray` / `EdgeArray` in three element types: `NodeArrayInt`, `NodeArrayDouble`, `NodeArrayBool`, `EdgeArrayInt`, `EdgeArrayDouble`, `EdgeArrayBool`

- [x] `GraphAttributes`: coordinates, width/height, labels

- [x] `GraphAttributes.graph`, `.has(flags)` (is an attribute group enabled), `.directed`

- [x] Styling: `Color`, `Shape`, `StrokeType`, `FillPattern`, `EdgeArrow`

- [x] Attribute flags to enable groups of attributes: `NODE_GRAPHICS`, `EDGE_GRAPHICS`, `NODE_LABEL`, `EDGE_LABEL`, `NODE_STYLE`, `EDGE_STYLE`, `EDGE_ARROW`, `ALL_ATTRIBUTES`

- [x] Layout configuration enums: `Orientation`, `RootSelection`, `RadialRootSelection`, `QualityVsSpeed`

- [x] Node fill/stroke color, shape, fill pattern, stroke width

- [x] Edge stroke, arrow type, bends

- [ ] 3D coordinates (`z`)

- [ ] `ClusterGraph` / `ClusterGraphAttributes`

- [ ] `GraphCopy` / `GraphReduction`

- [ ] Combinatorial embedding / dual graph

- [ ] Hypergraphs

## Layout algorithms

- [x] `SugiyamaLayout` (layered / hierarchical), with `number_of_crossings()` / `number_of_levels()` from the last call

- [x] `FMMMLayout` (fast multipole multilevel, force-directed)

- [x] `GEMLayout` (force-directed)

- [x] `SpringEmbedderKK` (Kamada-Kawai)

- [x] `StressMinimization`

- [x] `PivotMDS`

- [x] `PlanarizationLayout` (with optional orthogonal routing via `OrthoLayout`), with `number_of_crossings()` from the last call

- [x] `SchnyderLayout` (planar straight-line grid)

- [x] `TreeLayout`

- [x] `CircularLayout`

- [x] `BalloonLayout`

- [x] `RadialTreeLayout`

- [ ] `BertaultLayout` (deprioritized: five force-directed layouts already bound)

- [ ] `DavidsonHarelLayout` (deprioritized: force-directed, marginal over existing)

- [x] `MultilevelLayout` / `ModularMultilevelMixer`

- [ ] `FastMultipoleEmbedder` (deprioritized: FMMM already covers large-graph force layout)

- [ ] `NodeRespecterLayout` (bind on demand: only distinct hook is respecting real node sizes to avoid overlap)

- [x] Planar straight-line grid layouts: `FPPLayout`, `PlanarStraightLayout`, `PlanarDrawLayout`, `MixedModelLayout` (companions to `SchnyderLayout`)

- [x] `TutteLayout`

- [x] `DominanceLayout` / `VisibilityLayout` (upward, for DAGs)

- [x] `LinearLayout` (arc diagram)

- [ ] UML layouts (`PlanarizationLayoutUML`)

## Graph algorithms

### Connectivity and structure

- [x] `is_connected`, `is_biconnected`, `is_triconnected`

- [x] `is_acyclic`, `is_acyclic_undirected`

- [x] `is_bipartite` (with optional 2-coloring), `is_tree`, `is_forest`

- [x] `connected_components`, `strong_components`, `biconnected_components`

- [x] `topological_numbering`

- [x] `make_connected`, `make_biconnected`, `make_acyclic`

- [x] `is_two_edge_connected`, `is_regular`, `is_arborescence`

- [x] Simplicity: `is_simple`, `is_simple_undirected`, `has_self_loops`

- [x] cut vertices (`cut_vertices`) and bridges (`bridges`)

- [x] `triangulate`, `make_bimodal`

- [x] Triconnectivity: separation pair (`separation_pair`) and SPQR-tree summary (`spqr_tree_summary`)

- [x] node/edge k-connectivity values, global and local/Menger (`node_connectivity`, `edge_connectivity`)

- [ ] BC-trees / decomposition

### Planarity

- [x] `is_planar`

- [x] `planar_embed`, `planar_embed_planar_graph`, `represents_comb_embedding` (is an embedding currently in place)

- [x] Maximal planar subgraph (`maximal_planar_subgraph`)

- [x] Crossing number (`crossing_number`, heuristic via subgraph planarizer + edge insertion)

- [x] Edge insertion routing (`insert_edges`, routes edges through the fixed planar rest and returns the edges each one crosses)

- [ ] Upward planarity testing

- [ ] Cluster planarity

### Shortest paths

- [x] `dijkstra` (single-source, weighted; array form) and `dijkstra_tree` (also returns the shortest-path tree)

- [x] A* search (`a_star_search`, point-to-point; optional admissible heuristic)

- [x] Bellman-Ford (`bellman_ford`, negative weights, integer lengths - see item 10) and `bellman_ford_tree`

- [x] `shortest_paths()` - result object with distances, paths, predecessors, and reachability; picks Dijkstra or Bellman-Ford automatically

- [x] Unweighted BFS distances (`bfs_distances`, single-source)

### Spanning trees, flow, cut

- [x] `min_spanning_tree` (Prim), `make_minimum_spanning_tree` (Kruskal)

- [x] `max_flow` (Goldberg-Tarjan)

- [x] `min_cut` (Stoer-Wagner, global)

- [ ] Max flow: Edmonds-Karp, planar s-t variants

- [x] Min-cost flow (`min_cost_flow`, Reinelt)

- [x] s-t min cut, directed or undirected (`min_st_cut` returns an `STCut(value, edges)`; `st_cut` is the low-level form). Companion to global `min_cut` + `max_flow`. The node partition is not reported - see item 10

- [ ] Nagamochi-Ibaraki min cut

### Matching and coloring

- [x] `maximal_matching`

- [x] `maximum_matching_bipartite`

- [x] `node_coloring` (Recursive Largest First)

- [x] General maximum-weight matching (`maximum_weight_matching`, Blossom V)

- [ ] Other coloring heuristics (Berger-Rompel, Johnson, Wigderson, ...)

### Specialized / excluded algorithm families

- [x] Steiner trees (`steiner_tree`, Mehlhorn; OGDF has ~9 implementations)

- [ ] Graph spanners (Baswana-Sen, Berman, Elkin-Neiman, ...)

- [ ] PageRank (OGDF's `BasicPageRank` is undirected and min-max normalized to [0, 1] - degree-dominated and not canonical directed PageRank; use networkx/igraph for the standard measure)

- [ ] Voronoi diagrams / convex hull

- [ ] Planar separators (Lipton-Tarjan, Har-Peled, ...)

- [ ] Clustering (`Clusterer`, modified nibble)

- [ ] Edge-independent spanning trees

- [ ] Maximum density subgraph

- [ ] Max adjacency ordering

## Generators

- [x] `complete_graph`, `complete_bipartite_graph`

- [x] `wheel_graph`, `cube_graph`, `grid_graph`, `petersen_graph`

- [x] `regular_tree`, `empty_graph`

- [x] `random_graph`, `random_tree`, `random_digraph`

- [x] `random_regular_graph`, `random_biconnected_graph`

- [x] `random_planar_connected_graph`

- [x] `circulant_graph`, `globe_graph`, `complete_kpartite_graph`, `regular_lattice_graph`

- [x] Graph products: `cartesian_product`, `tensor_product`, `strong_product`, `lexicographical_product`

- [x] Random models: `preferential_attachment_graph`, `random_chung_lu_graph`, `random_watts_strogatz_graph`, `random_waxman_graph`

- [x] `random_geometric_cube_graph`, `random_hierarchy`, `random_series_parallel_dag`

- [x] `random_triconnected_graph`, `random_planar_biconnected_graph`, `random_planar_triconnected_graph`

- [x] Graph operations: `graph_union`, `complement`, `suspension`

## File I/O

### Interchange formats (read and write with attributes)

- [x] GML (`read_gml` / `write_gml`)

- [x] GraphML (`read_graphml` / `write_graphml`)

- [x] DOT (`read_dot` / `write_dot`)

- [x] GEXF (`read_gexf` / `write_gexf`)

- [x] GDF (`read_gdf` / `write_gdf`)

- [x] TLP (`read_tlp` / `write_tlp`)

- [x] Generic `read` / `write` (format inferred from extension)

- [ ] LEDA, Chaco (graph-only, no attributes)

- [ ] DL, Rudy

- [ ] Graph6 / Digraph6 / Sparse6

- [ ] STP (Steiner), DMF (max-flow), Rome, benchmark formats

### Drawing output

- [x] SVG (`draw_svg` / `to_svg`)

- [x] TikZ (`draw_tikz` / `to_tikz`)

## Python layer

Not bindings of OGDF classes, but the API that makes the binding usable from
Python. Covered in depth in [Getting Started](getting-started.md).

### Diagnostics

- [x] `about()` / `about_text()` / `python -m ogdf` - package and OGDF versions, the pinned OGDF tag the linked libraries were built from, OGDF's compiled-in configuration, platform, compiler, and available capabilities

- [x] `build_info()` - the compiled-in half of the above

### Errors and preconditions

- [x] Exception taxonomy: `OGDFError`, `PreconditionError`, `InvalidGraphError`, `UnsupportedFormatError`, `AlgorithmError` (the argument-shaped ones also subclass `ValueError`, `AlgorithmError` subclasses `RuntimeError`)

- [x] Enforcement of every documented precondition before entering OGDF, whose assertions are compiled out of a release build

- [x] Argument checks: arrays belonging to another graph, `None` nodes, negative weights where non-negative is assumed, source equal to sink

- [x] `requirements()`, `validate()`, `is_valid_for()`, `check()`, `operations()`, `graph_report()`

- [ ] Transactional guarantees for mutating operations that fail partway (currently: preconditions are checked up front, so the mutators either run or do not start)

### Interoperability

- [x] `from_edges` / `to_edges` (edge lists, with a caller-supplied key mapping)

- [x] `from_networkx` / `to_networkx` (all four NetworkX classes; directedness, multiedges, node identity, and layout coordinates handled explicitly). NetworkX is an optional dependency, imported lazily

- [x] Arrays to and from Python containers: `node_array_to_dict`, `edge_array_to_dict`, `node_array_to_list`, `edge_array_to_list`, `fill_node_array`, `fill_edge_array`

- [x] Results as ordinary collections: `nodes_where`, `edges_where`

- [ ] igraph adapters (bind on demand)

- [ ] pandas / polars node and edge tables

- [ ] NumPy views over `NodeArray` / `EdgeArray` without a copy

### Reproducibility

- [x] `set_seed`, `get_seed`, `new_seed`, and the `seeded(n)` context manager over OGDF's process-wide random engine (`seed_random_engine`, `draw_random_seed`)

- [x] `provenance(**settings)` - JSON-serializable metadata recording seed, versions, platform, and algorithm settings

- [x] Achieved objective values from the heuristic layouts, so runs and seeds can be compared numerically

- [ ] A serializable "layout recipe" (graph hash + algorithm + options + seed + versions + output metrics)

### Results

- [x] Result objects with named fields, alongside the array-output form, which stays the bulk-calling path: `ShortestPaths` (distances, paths, predecessors, reachability) and `STCut` (value and cut edges)

- [x] `shortest_paths()` picks Dijkstra or Bellman-Ford automatically and reports unreachability as `math.inf` / `None` rather than OGDF's raw sentinel

- [ ] Result objects for the remaining array-output algorithms (matching, colouring, components)

### Placing a drawing

- [x] Coordinate transforms: `normalize`, `center`, `translate`, `scale`, `fit_to_box`, `pack_components` (the last binding OGDF's `TileToRowsCCPacker`). All move edge bends as well as node coordinates

- [x] Low-level forms, if you need them: `translate_drawing`, `scale_drawing`, `fit_scale`, `tile_components`

- [ ] Rotation and reflection

- [ ] Per-component transforms (fit each component to its own box)

### Measuring a drawing

- [x] `count_crossings`, `edge_lengths`, `bounding_box`, `node_overlaps`, `min_angle` (angular resolution), `stress` - all computed over the drawn polylines, so bends count

- [x] `drawing_metrics()` aggregates them into one serializable dict; `compare_layouts()` runs several layouts and ranks them

- [ ] Edge-edge and node-edge distance, symmetry, and orthogonality metrics

- [ ] A benchmark runner recording runtime and memory alongside the metrics

### Workflow

- [x] `layout(graph, algorithm=FMMMLayout, **options)` - preconditions, seeding, the layout, packing, and fit-to-box in one call. The algorithm is a class by default so it stays type-checked; a string is accepted for config-driven use, and `layout_names()` lists what resolves

- [ ] A serializable "layout recipe" that replays a drawing from graph + algorithm + options + seed

### Not yet provided

- [ ] Themes, palettes, and style-by-attribute helpers

- [ ] Notebook / interactive HTML output beyond the SVG string

- [ ] A CLI for converting, laying out, and rendering graph files

## Excluded subsystems

Whole OGDF modules that are out of scope for the current curated subset:

- [ ] Clustered graphs and cluster planarity / layout

- [ ] UML diagram support

- [ ] Hypergraphs

- Upward drawing and upward planarity are *not* a wholesale exclusion: `DominanceLayout` / `VisibilityLayout` (upward drawing for DAGs) are bound, and upward planarity testing is tracked as an open gap in the [Planarity](#planarity) section

- [ ] Simultaneous embedding (SEFE) / SyncPlan

- [ ] Augmentation (planarity / connectivity augmentation)

- [ ] Rectangle / component packing

- [ ] LP solver (COIN) interface
