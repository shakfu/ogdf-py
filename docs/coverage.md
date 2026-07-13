# Coverage

This page tracks what OGDF functionality is exposed by `ogdf-py`. It is a living checklist: `ogdf-py` is a **curated subset**, so most of OGDF is intentionally excluded.

**Legend:** `[x]` = bound and available in Python, `[ ]` = not (yet) bound. Unbound items scheduled for the next additions may be tagged `**(priority)**`; see the [Priority roadmap](#priority-roadmap).

**Scope rationale.** The binding targets OGDF's genuine differentiators for Python users - **graph drawing** and **planarity** - plus a **core set of common graph algorithms** (even where these overlap networkx/scipy) for a self-contained experience. Because that common-algorithm core is explicitly in scope, canonical routines users reach for next to what is already bound - notably **A\*** (alongside `dijkstra`/`bellman_ford`) - are treated as in-scope gaps to close, not as exotic exclusions. That said, the core covers algorithms OGDF actually implements well: **PageRank** is intentionally omitted because OGDF only ships an undirected, [0, 1]-normalized variant that is degree-dominated and not the canonical directed measure (see below). Genuinely exotic or specialized algorithms, and large subsystems (clustering, UML, hypergraphs, cluster planarity, SEFE), are excluded unless there is concrete demand. Contributions that move an item from `[ ]` to `[x]` are welcome.

## Priority roadmap

Highest-value gaps given the drawing + planarity focus and the common-algorithm core. Tiers 1 and 2 are complete; nothing is currently scheduled. Future priorities, when chosen, are tagged `**(priority)**` in the sections below.

**Done (Tier 1):**

1. **Planar straight-line grid layouts** - `FPPLayout`, `PlanarStraightLayout`, `PlanarDrawLayout`, `MixedModelLayout`, completing the planar-drawing family alongside `SchnyderLayout`.

2. **Common shortest-path gap** - `a_star_search`. (PageRank was evaluated and dropped: OGDF's `BasicPageRank` is undirected and [0, 1]-normalized, so it is degree-dominated and not canonical directed PageRank - little unique value over `node.degree`. Directed PageRank is left to networkx/igraph rather than hand-rolled here.)

3. **Crossing number** - `crossing_number`, the heuristic minimum computed by the subgraph planarizer, now a standalone call rather than a hidden step in `PlanarizationLayout`.

**Done (Tier 2):**

4. **s-t min cut** (`min_st_cut`, directed or undirected) and **k-connectivity** (`node_connectivity`, `edge_connectivity`, global and local) - completing the flow/cut and connectivity families that were only partially bound.

**Done (Tier 2, follow-on):**

5. **Edge-insertion routing** (`insert_edges`) - routes a chosen set of edges through the rest of the graph (which must be planar once they are removed) and returns, per edge, the original edges it crosses. Uses the variable-embedding inserter with no remove-reinsert, so crossings are attributed cleanly to the inserted edges rather than re-routed across the whole drawing.

**Not scheduled:**

- Planarity depth: combinatorial embedding + dual graph, upward planarity testing, planar separators.

## Graph model and attributes

- [x] `Graph`, `Node`, `Edge`, node/edge iteration

- [x] `NodeArray` / `EdgeArray` (int, double, bool)

- [x] `GraphAttributes`: coordinates, width/height, labels

- [x] Styling: `Color`, `Shape`, `StrokeType`, `FillPattern`, `EdgeArrow`

- [x] Node fill/stroke color, shape, fill pattern, stroke width

- [x] Edge stroke, arrow type, bends

- [ ] 3D coordinates (`z`)

- [ ] `ClusterGraph` / `ClusterGraphAttributes`

- [ ] `GraphCopy` / `GraphReduction`

- [ ] Combinatorial embedding / dual graph

- [ ] Hypergraphs

## Layout algorithms

- [x] `SugiyamaLayout` (layered / hierarchical)

- [x] `FMMMLayout` (fast multipole multilevel, force-directed)

- [x] `GEMLayout` (force-directed)

- [x] `SpringEmbedderKK` (Kamada-Kawai)

- [x] `StressMinimization`

- [x] `PivotMDS`

- [x] `PlanarizationLayout` (with optional orthogonal routing via `OrthoLayout`)

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

- [x] cut vertices (`cut_vertices`) and bridges (`bridges`)

- [x] `triangulate`, `make_bimodal`

- [x] Triconnectivity: separation pair (`separation_pair`) and SPQR-tree summary (`spqr_tree_summary`)

- [x] node/edge k-connectivity values, global and local/Menger (`node_connectivity`, `edge_connectivity`)

- [ ] BC-trees / decomposition

### Planarity

- [x] `is_planar`

- [x] `planar_embed`, `planar_embed_planar_graph`

- [x] Maximal planar subgraph (`maximal_planar_subgraph`)

- [x] Crossing number (`crossing_number`, heuristic via subgraph planarizer + edge insertion)

- [x] Edge insertion routing (`insert_edges`, routes edges through the fixed planar rest and returns the edges each one crosses)

- [ ] Upward planarity testing

- [ ] Cluster planarity

### Shortest paths

- [x] `dijkstra` (single-source, weighted)

- [x] A* search (`a_star_search`, point-to-point; optional admissible heuristic)

- [x] Bellman-Ford (`bellman_ford`, negative weights)

- [x] Unweighted BFS distances (`bfs_distances`, single-source)

### Spanning trees, flow, cut

- [x] `min_spanning_tree` (Prim), `make_minimum_spanning_tree` (Kruskal)

- [x] `max_flow` (Goldberg-Tarjan)

- [x] `min_cut` (Stoer-Wagner, global)

- [ ] Max flow: Edmonds-Karp, planar s-t variants

- [x] Min-cost flow (`min_cost_flow`, Reinelt)

- [x] s-t min cut, directed or undirected (`min_st_cut`, returns value and cut edges; companion to global `min_cut` + `max_flow`)

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

## Excluded subsystems

Whole OGDF modules that are out of scope for the current curated subset:

- [ ] Clustered graphs and cluster planarity / layout

- [ ] UML diagram support

- [ ] Hypergraphs

- [ ] Upward planarity and upward drawing

- [ ] Simultaneous embedding (SEFE) / SyncPlan

- [ ] Augmentation (planarity / connectivity augmentation)

- [ ] Rectangle / component packing

- [ ] LP solver (COIN) interface
