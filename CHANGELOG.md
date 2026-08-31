# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

**Results**

- Result objects, alongside the existing array-output functions rather than replacing them. `shortest_paths(graph, source, weight=None, *, directed=False, algorithm="auto")` returns a `ShortestPaths` with `distance()`, `path_to()`, `nodes_to()`, `predecessor_edge()`, `reachable()`, `unreachable_nodes()`, and `distances()`. `dijkstra` and `bellman_ford` were already building the shortest-path tree internally and discarding it; this keeps it. Unreachable nodes report `math.inf` and `None` instead of OGDF's raw sentinel, and `algorithm="auto"` picks Bellman-Ford when an `EdgeArrayInt` holds a negative length, Dijkstra otherwise. A reachable negative cycle raises `AlgorithmError` rather than returning meaningless distances.

- `min_st_cut` now returns an `STCut` named tuple, so the value and edges are reachable by name (`cut.value`, `cut.edges`) as well as by unpacking. The return shape is unchanged, so existing `value, edges = min_st_cut(...)` code keeps working.

- Low-level primitives behind the above: `dijkstra_tree`, `bellman_ford_tree`, and `st_cut`.

**Placing a drawing**

- Coordinate transforms for placing a finished drawing: `translate`, `center`, `normalize` (lower-left corner to the origin), `scale` (about the centre, the origin, the lower-left corner, or an explicit point), `fit_to_box`, and `pack_components`. Every one moves edge bend points as well as node coordinates, so a drawing produced by a routing layout is not torn apart - which is also why they are implemented natively, since bends are otherwise only reachable through `add_bend` / `clear_bends`.

- `scale` leaves node sizes alone by default, since scaling up is usually how overlapping nodes get separated; `scale_node_sizes=True` scales the whole picture. `fit_to_box` preserves aspect ratio, returns the factor it applied, and scales node sizes by default so the fit is exact; with `scale_node_sizes=False` the factor is solved for by bisection rather than estimated, so the fit stays exact while node boxes keep their size.

- `pack_components` arranges disconnected components side by side instead of piled at a common origin, binding OGDF's `TileToRowsCCPacker`. Returns the component count and leaves a connected graph untouched.

**Measuring a drawing**

- Drawing-quality metrics, so layouts can be compared on numbers instead of by eye: `count_crossings`, `edge_lengths`, `bounding_box`, `node_overlaps`, `min_angle` (angular resolution), and `stress`. All are computed over the drawn polylines, so edge bends are respected rather than treated as straight lines.

- `drawing_metrics(attributes)` aggregates them into one plain dict - crossings, the edge-length distribution and its scale-free coefficient of variation, width/height/area/aspect ratio, node overlap, angular resolution, and stress - ready to serialize alongside `provenance()`.

- `compare_layouts(graph, layouts, *, seed=None)` runs several layouts on one graph, each with a fresh `GraphAttributes`, and returns their metrics ranked by crossings then stress. A layout whose preconditions the graph fails is reported with an `error` key and sorted last instead of aborting the comparison; `seed` makes randomized layouts comparable like for like.

**Workflow**

- `layout(graph, algorithm=FMMMLayout, **options)` - one call from a graph to a placed drawing, composing precondition checks, seeding, the layout itself, optional component packing, and fit-to-box. The algorithm is a class by default, so it stays completable in an editor and checkable by mypy; a string is accepted for config-driven use, with `layout_names()` listing what resolves. Options are forwarded to the layout's setters through a mechanical `set_X` mapping derived from the bindings, so it cannot drift, and an unknown option raises `TypeError` naming what that layout does accept. Returns the `GraphAttributes`; metrics and provenance are deliberately left as separate calls, since the metrics are quadratic.

**Documentation and tests**

- Documentation: a Drawing Metrics page explaining what each metric means and how to read it, and the layout selection guide's comparison example now uses `compare_layouts` instead of a hand-rolled loop.

- Documented how the metrics read on real drawings: self-loops contribute length 0 (a straight-line drawing gives them no extent), `min_angle` is a worst case that a single pair of collinear edges sends to 0, and `stress` is a sum over node pairs so it grows with the graph and should only be compared between layouts of the same graph.

- `tests/test_docs.py` verifies the concrete output values printed in the documentation - the capability counts in the sample installation report, the `drawing_metrics` example, the recipe's build order, and the small inline `# result` comments - by re-deriving each and comparing.

- Documentation: a `layout()` section in the getting-started guide, a Placing the drawing section on the metrics page covering the transforms, and a `coverage.md` reorganised so the Python layer lists results, placement, measurement, and workflow as their own groups rather than filing completed work under "not yet provided".

### Changed

- `min_st_cut` deliberately does **not** report the node partition, and the documentation says why. OGDF's `MinSTCutMaxFlow` exposes `isInFrontCut` / `isInBackCut`, which look like the two sides of the cut but are the extreme minimum cuts nearest the source and nearest the sink. When the minimum cut is not unique those are different cuts, and neither is guaranteed to correspond to the edge list returned alongside them - on the complete digraph on 20 nodes the front cut is `{s}` while the returned edges are the sink's in-edges, so the two together describe no single cut. Callers who need the partition should derive it from the cut edges, which is consistent by construction; a test asserts that removing them really does separate source from sink.

- Algorithm docstrings now state provenance and conventions: whether the result is exact, heuristic, or approximate (`node_coloring` is a heuristic upper bound, `steiner_tree` a 2-approximation, `maximal_matching` maximal but not maximum), whether edge direction is honoured, how parallel edges are treated, and what an unreachable node's sentinel is.

- `bellman_ford` keeps integer edge lengths while `dijkstra` and `a_star_search` take doubles. This inconsistency is now documented rather than removed: OGDF's `ShortestPathModule` interface is defined over `int` and ships no floating-point Bellman-Ford, so closing the gap would mean reimplementing the algorithm instead of binding one - and the two are not interchangeable anyway, since Dijkstra rejects the negative weights Bellman-Ford exists for. `shortest_paths()` accepts either array type.

### Fixed

- Two documentation examples stated values that were never produced by running them: the `drawing_metrics` output in `docs/metrics.md` was written by hand rather than measured, and the topological order in the DAG recipe was a valid ordering but not the one the snippet prints. Both are now the real output, and `tests/test_docs.py` checks them.

- The capability counts in the sample `python -m ogdf` report had gone stale as more functions were bound (82/18/22 rather than the current 99/19/27).

## [0.4.0]

### Added

- `ogdf.about()` and `ogdf.about_text()` (also `python -m ogdf`): an installation diagnostic reporting the package version, the OGDF version and the pinned OGDF tag the linked static libraries were built from, OGDF's compiled-in configuration (system, LP solver, memory manager), the platform, the compiler, and a count and listing of the available capabilities. The pinned tag is baked in at build time, so the report describes the extension actually loaded.

- Offline and locked-down source builds. `scripts/bootstrap_ogdf.py` can now take the OGDF source from a local archive (`--archive`, `OGDF_ARCHIVE`) or an existing checkout (`--source-dir`, `OGDF_SOURCE_DIR`) instead of cloning, and `--offline` / `OGDF_OFFLINE=1` forbids network access outright. CMake accepts `-DOGDF_PREBUILT_DIR=/path/to/ogdf` (or the matching environment variable) to link against a separately built OGDF and skip the bootstrap entirely.

- Documented support matrix: which platform/architecture/CPython combinations have wheels, what a source build requires (tools, disk space, expected build time), and the three offline installation paths.

- CI coverage for the claims above: an `offline-build` job asserting that an offline bootstrap refuses to clone (and says how to vendor the source) and then builds and tests from a vendored checkout with `OGDF_OFFLINE=1`; and wheel tests that now import the wheel, print its installation report, and run the full suite - including the interop layer, by installing the optional `networkx` dependency.

- Exception taxonomy: `OGDFError` and, under it, `PreconditionError` (a `ValueError`), `InvalidGraphError`, `UnsupportedFormatError` (a `ValueError`), and `AlgorithmError` (a `RuntimeError`). The builtin mix-ins keep existing `except ValueError` / `except RuntimeError` code working.

- Consistent precondition enforcement. OGDF documents preconditions but compiles its assertions out of a release build, so violating one was undefined behaviour rather than a diagnosable error. Every wrapper with a documented precondition now checks it first: `SchnyderLayout`, `TreeLayout` (forest), `RadialTreeLayout` (tree), `TutteLayout` (triconnected planar), `DominanceLayout` / `VisibilityLayout` (DAG), `SpringEmbedderKK` (connected), `triangulate` (simple, connected, planar *embedded*), `topological_numbering` (DAG), `min_cut`, `maximum_matching_bipartite`, and `spqr_tree_summary`. The bindings additionally reject arrays belonging to a different graph than the one passed in, `None` node arguments, negative weights where the algorithm assumes non-negative ones (`dijkstra`, `a_star_search`, `max_flow`, `min_cut`, `min_st_cut`, `steiner_tree`), and a source equal to its sink.

- Validation helpers that report instead of raising: `requirements(name)`, `validate(name, graph)` (the unmet requirements, in check order), `is_valid_for(name, graph)`, `check(name, graph)`, `operations()`, and `graph_report(graph)` - a full structural description of a graph in one call. The requirement table mirrors the compiled-in checks, so the two cannot disagree.

- Predicates `is_simple`, `is_simple_undirected`, `has_self_loops`, and `represents_comb_embedding` (whether a planar embedding is currently in place).

- Python interoperability layer. `from_edges` / `to_edges` build a graph from - and report it back as - an ordinary edge list, returning a mapping from the caller's own keys to `Node` handles; extra tuple entries are ignored so a weighted `(u, v, w)` list works unchanged, and parallel edges and self-loops are preserved.

- `from_networkx` / `to_networkx` for all four NetworkX classes, with explicit handling of directedness, multiedges, node identity, and layout coordinates. `from_networkx(graph_attributes=True)` also returns a `GraphAttributes` whose `directed` flag matches the input and can copy a NetworkX node attribute into the node labels; `to_networkx` picks a lossless NetworkX class by default and copies `x`, `y`, `width`, `height`, and `label` back out, making a laid-out OGDF drawing directly plottable. NetworkX is an optional dependency, imported lazily.

- Array conversion helpers: `node_array_to_dict`, `edge_array_to_dict`, `node_array_to_list`, `edge_array_to_list`, `fill_node_array`, and `fill_edge_array` - keyed by `node.index` / `edge.index` by default, or by a caller-supplied mapping, with a documented node-identity policy.

- Result helpers `nodes_where` and `edges_where`, which turn the boolean-array output convention into ordinary Python lists of nodes or edges (a spanning tree, a matching, a cut).

- `GraphAttributes.graph` (the graph being described), `GraphAttributes.has(flags)` (whether an attribute group is enabled before reading it), and a readable/writable `GraphAttributes.directed`.

- Reproducibility. `set_seed`, `get_seed`, `new_seed`, and the `seeded(n)` context manager wrap OGDF's process-wide random engine, making every stochastic generator, layout, and heuristic reproducible from a recorded seed. `provenance(**settings)` returns JSON-serializable metadata - seed, package version, OGDF version and pinned tag, platform, and the algorithm settings passed in - to store alongside a result. Documented what is and is not guaranteed: same seed and same build reproduce a result exactly; across platforms, compilers, or OGDF versions they do not.

- Heuristic algorithms now report their achieved objective value: `SugiyamaLayout.number_of_crossings()` and `.number_of_levels()`, and `PlanarizationLayout.number_of_crossings()`, so runs and seeds can be compared numerically.

- Reproducibility tests asserting that a seed reproduces both the generated graph and its coordinates, and that different seeds diverge.

- Documentation: a layout selection guide (`docs/choosing-a-layout.md`) organising all nineteen layouts by graph structure, constraint, scale, and intended output, with guidance on directedness, disconnected graphs, multigraphs, determinism, and how to compare candidates numerically; and four end-to-end recipes (`docs/recipes.md`) - NetworkX to SVG, DAG to layered SVG, planar graph to TikZ, and a weighted graph to an annotated drawing. Every recipe is executed by `tests/test_recipes.py` so it cannot silently rot.

- Low-level `seed_random_engine` and `draw_random_seed` bindings, wrapped by `set_seed` / `new_seed`.

- Tests for invalid, empty, disconnected, cyclic, non-planar, non-bipartite, negative-weight, cross-graph-array, and duplicate-endpoint inputs.

### Changed

- `docs/coverage.md` now records the Python layer that is not a binding of anything - diagnostics, the exception taxonomy, interoperability, and reproducibility - alongside the OGDF inventory, and its priority roadmap names result ergonomics as the next item: `dijkstra` and `bellman_ford` already compute predecessor arrays internally and discard them, `max_flow` reports no source-side partition, and `bellman_ford`'s integer edge lengths are still inconsistent with the `double` weights used by `dijkstra` and `a_star_search`.

- `__version__` is single-sourced from the installed distribution metadata (falling back to the version CMake compiled into the extension) instead of being duplicated in `src/ogdf/__init__.py`. Both derive from `pyproject.toml`, and `tests/test_about.py` asserts they agree, so a stale extension now fails the suite.

- Build failures now identify the failing stage. The bootstrap distinguishes a missing tool, a failed source fetch, a failed CMake configuration (typically no C++17 compiler), and a failed compilation; CMake names which of the OGDF and COIN static libraries is missing and tailors the remedy to whether a prebuilt tree or offline mode was requested.

- The pinned OGDF tag now lives in a single place, `scripts/ogdf-tag.txt`, read by both the bootstrap script and CMake, so the tag reported by `ogdf.about()` cannot drift from the libraries that were linked.

## [0.3.0]

### Added

- Planar layouts: `FPPLayout`, `PlanarStraightLayout`, `PlanarDrawLayout`, and `MixedModelLayout` - straight-line and mixed-model planar grid drawings, completing the planar-drawing family alongside `SchnyderLayout`. Each validates that the input is a simple planar graph with at least 3 nodes.

- Shortest paths: `a_star_search`, point-to-point A* with an optional admissible heuristic; returns the path length and edges, or `None` if the target is unreachable.

- Crossing minimization: `crossing_number` (heuristic minimum crossings via the subgraph planarizer) and `insert_edges` (routes a chosen set of edges through the otherwise-planar rest of the graph and returns, per edge, the original edges it crosses).

- Flow / cut and connectivity: `min_st_cut` (directed or undirected s-t minimum cut, returning the value and the cut edges) and `node_connectivity` / `edge_connectivity` (global and local/Menger k-connectivity).

- Documentation: expanded the coverage checklist with a priority roadmap.

## [0.2.0]

### Added

- Layouts: `RadialTreeLayout`, `LinearLayout` (arc diagram), `TutteLayout` (convex planar), `DominanceLayout` / `VisibilityLayout` (upward, for DAGs), `MultilevelLayout` / `ModularMultilevelMixer` (large graphs), and `BalloonLayout`.

- Algorithms: cut vertices (`cut_vertices`) and bridges (`bridges`), Bellman-Ford shortest paths (`bellman_ford`), minimum-cost flow (`min_cost_flow`), general maximum-weight matching (`maximum_weight_matching`, Blossom V), minimum Steiner tree (`steiner_tree`, Mehlhorn), maximal planar subgraph (`maximal_planar_subgraph`), and triconnectivity via `separation_pair` and `spqr_tree_summary`.

- Cross-platform Python bootstrap (`scripts/bootstrap_ogdf.py`) replacing the bash script; generalized CMake linking (MSVC-aware); Windows build+test CI job.

- MkDocs documentation site (`docs/`) with a coverage checklist and a Gallery page rendering the demo drawings; `make docs`, `make docs-serve`, `make docs-deploy`.

- Demos: gallery entries for the new layouts, and algorithm visualizations for cut vertices/bridges, maximum-weight matching, Bellman-Ford distances, minimum-cost flow, the minimum Steiner tree, and the maximal planar subgraph.

- Generators: circulant, complete-k-partite, globe, regular-lattice; graph products (cartesian, tensor, strong, lexicographical); operations (union, complement, suspension); and random models (preferential attachment, Chung-Lu, Watts-Strogatz, Waxman, geometric-cube, hierarchy, series-parallel DAG, triconnected, planar-biconnected, planar-triconnected).

- Predicates and small algorithms: `is_two_edge_connected`, `is_regular`, `is_arborescence`, `triangulate`, `make_bimodal`, and `bfs_distances` (unweighted single-source distances).

- Windows support: the release workflow now builds Windows (AMD64) wheels alongside Linux and macOS, and the wheel matrix covers CPython 3.10-3.14.

### Fixed

- Removed the persistent CMake `build-dir` from `pyproject.toml`. Sharing it between editable installs and wheel builds could leave stale objects, so a `uv build --wheel` sometimes omitted recently-added functions. Each build now uses a fresh directory (OGDF is prebuilt, so this stays fast).

- MSVC build: replaced the non-standard `M_PI` (undefined on MSVC) with an explicit constant so the extension compiles on Windows.

## [0.1.1]

### Added

- OGDF bindings (curated subset): `Graph`/`Node`/`Edge` with iteration; `NodeArray`/`EdgeArray` in int/double/bool; `GraphAttributes` with coordinates, size, labels, and styling (colors, shapes, fill patterns, stroke, edge arrows, bends).

- Layout algorithms: `SugiyamaLayout`, `FMMMLayout`, `GEMLayout`, `SpringEmbedderKK`, `StressMinimization`, `PivotMDS`, `PlanarizationLayout` (with optional orthogonal routing), `SchnyderLayout`, `TreeLayout`, `CircularLayout`.

- Core graph algorithms: connectivity/structure predicates, connected / strong / biconnected components, topological numbering, Dijkstra shortest paths, minimum spanning tree, maximum flow, global minimum cut, matching, node coloring, and planar embedding.

- Graph generators: complete, complete-bipartite, wheel, cube, grid, Petersen, regular tree, plus random graphs, trees, digraphs, and regular / biconnected / planar variants.

- File I/O: interchange formats GML, GraphML, DOT, GEXF, GDF, TLP (with extension-based `read`/`write`) and drawing output as SVG and TikZ.

- `demos/` folder with illustrative scripts (layout gallery, styling showcase, algorithm visualizations, generator zoo, I/O round-trips) writing to `build/demo-output`; `make demos` also builds a self-contained HTML gallery (`index.html`) of every drawing.

- Bindings split into modular translation units (`bind_graph`, `bind_layouts`, `bind_algorithms`, `bind_io`, `bind_generators`).

- Auto-generated `_core.pyi` type stub for typed usage and IDE completion.

- `cibuildwheel` release workflow building CPython 3.10-3.13 wheels for Linux (x86_64, aarch64) and macOS (x86_64, arm64) on native runners, bootstrapping OGDF once per platform; trusted-publishing jobs for TestPyPI/PyPI on tags.

- CMake auto-bootstraps OGDF if missing, so `pip install` from an sdist works without a manual step (Unix only).

### Changed

- Reproducible OGDF dependency: `scripts/bootstrap_ogdf.py` (cross-platform: Linux, macOS, Windows) shallow-clones OGDF at a pinned tag (`foxglove-202510`) and builds its static libraries from source; the extension links them. `make build`/`make sync` auto-bootstrap if needed. Replaces reliance on a manually placed OGDF checkout.

- Persist the CMake build directory so only the bindings recompile on edits.

### Fixed

- `make build` targeted the wrong package name (`ogdf` vs `ogdf-py`), making it a silent no-op; it now rebuilds correctly.

- The generic `write` now raises `ValueError` for attribute-incapable formats (e.g. LEDA, Chaco) instead of crashing the interpreter.

## [0.1.0]

### Added

- Initial project structure

- Core module with example functions

- Test suite with pytest

- Build system using scikit-build-core
