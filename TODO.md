# TODO

IDs refer to findings in `REVIEW.md`.

## Critical

- [x] C1: `GraphAttributes` accessors, layouts, metrics, transforms and SVG/TikZ output check the attribute flags they need.
- [x] C2: Node/Edge handles from iterators, `source`/`target` and returned lists keep their `Graph` alive.
- [x] C3: Handles detect that their element was deleted (`clear`, readers, generators, mutators).
- [x] C4: Every array argument is checked against its graph; `NodeArray`/`EdgeArray` indexing rejects foreign handles.
- [x] C5: Readers check that the `GraphAttributes` belongs to the `Graph`.
- [x] C6: `steiner_tree` and `insert_edges` reject `None`, foreign handles and non-node items; Steiner terminals must share a component.
- [x] C7 / P1: `FPPLayout`, `MixedModelLayout`, `SchnyderLayout`, `DominanceLayout`, `VisibilityLayout` require a connected graph, in C++ and in `_validate._REQUIREMENTS`.
- [x] C8: `min_spanning_tree` returns a spanning forest on disconnected input and 0.0 on an empty graph.

## High

- [x] C9: `planar_embed_planar_graph` rejects non-planar input instead of modifying it.
- [x] C10: Generators validate sizes, degrees and parity, and reject aliased graph arguments; `cube_graph` rejects overflow; `SugiyamaLayout.set_runs` rejects 0.
- [x] C11: `min_cost_flow` checks connectivity, `lb <= ub`, zero supply sum and same-graph arrays.
- [x] C12: `PivotMDS.set_edge_costs` requires finite positive costs.
- [x] C13: `bellman_ford` maps the `INT_MAX` sentinel and cannot overflow.
- [x] C14: `require_non_negative` rejects NaN.
- [x] P2: `set_seed` accepts every value `new_seed` returns.
- [x] P3: `to_networkx` directedness does not depend on the `GraphAttributes.directed` default.
- [x] B1: Project relicensed to GPL v2 or v3 with OGDF's linking exception; wheels ship OGDF's licence texts.
- [x] B2: `make clean` does not touch `.venv` or `thirdparty`.

## Medium

- [x] Handle tracking overhead. Now within noise of HEAD built locally: `random_graph` with 1.2M elements 0.16 s, 200k `NodeArray` writes 7 ms, peak RSS +12 MB.
- [ ] Hidden edges (`HiddenEdgeSet`) are not in `Graph::edges` when a graph is destroyed, so their Python handles are not invalidated. No binding hides edges on a user graph today.
- [ ] A stale handle fails with nanobind's generic "incompatible function arguments" `TypeError`. A clearer message would need a check per access, which is what the tracker avoids.
- [ ] T4: `tests/test_safety.py` covers each critical class in-process, so a regression to a segfault aborts the whole run. Run them in subprocesses to report each crash separately.
- [x] P4: `SpringEmbedderKK`, `StressMinimization`, `PivotMDS` are classified as layouts.
- [x] P5: The `"forest"` predicate matches what `TreeLayout` accepts.
- [x] P6: `shortest_paths` rejects Bellman-Ford with `directed=False`.
- [x] P7: `layout(seed=)` and `compare_layouts(seed=)` update `provenance()`.
- [ ] P8: `seeded()` does not replay the outer random stream on exit.
- [x] P9: `fill_node_array` with `keys` skips unmapped nodes.
- [x] P10: `fit_to_box` rejects non-finite sizes.
- [ ] P11: Dijkstra results do not treat `2**31-1` as the unreachable sentinel.
- [x] C15: `separation_pair` handles non-biconnected input.
- [x] C16: Translate `ogdf::Exception` and `MatchingBlossomV` errors into `OGDFError` subclasses.
- [ ] C17: Release the GIL in layout and algorithm calls without Python callbacks. Calls that add or delete elements must keep it: `HandleTracker` (`errors.h`) calls into nanobind from OGDF's observer callbacks.
- [x] C18: Foreign source/target nodes and `new_edge` across graphs are rejected.
- [x] B3: Exclude C++ sources from the wheel.
- [x] B4: Pin OGDF by commit SHA and verify it after clone.
- [x] B5: Fix or remove the Linux OGDF cache in `build-publish.yml`. Unverified until the next wheel run: the cache step should log "Cache saved" on Linux.
- [ ] B6: Add the runner image to OGDF cache keys (the wheel keys now include the cibuildwheel version and deployment target).
- [x] B7: Re-fetch OGDF when `ogdf-tag.txt` changes.
- [ ] B8: Pin GitHub Actions by SHA.
- [x] B9: Test Python 3.10 and 3.14, and macOS, on pushes to main.
- [x] B10: Remove or restrict `make publish` / `make publish-test`.
- [x] T1 (part): `make_connected`, `make_biconnected`, `make_acyclic`, `is_triconnected` are tested.
- [ ] T1 (rest): the other 44 untested exports.
- [ ] T2: Tests for layout setters with a measurable effect.
- [ ] T3: Strengthen the TikZ, bends and I/O round-trip tests.
- [x] T5: Resolve the packing and augmentation contradictions in `docs/coverage.md`.

## Low

- [x] `tarfile.extractall` uses `filter="data"`.
- [x] `pyproject.toml`: SPDX licence string, real keywords, `[project.urls]`, bounded build requirements.
- [x] Exclude `.github/` and `TODO.md` from the sdist. `docs/` and `demos/` stay: `tests/test_docs.py` reads `docs/`.
- [x] `make qa` runs the same mypy scope as CI.
- [x] `distclean` removes what its help text says.
- [x] `OGDF_LIB` in the Makefile matches the Windows library name.
- [x] ruff and mypy cover `scripts/`.
- [ ] ruff and mypy cover `demos/`.
- [x] CI runs `mkdocs build --strict`.
- [x] Decide whether `publish-pypi` should depend on `publish-testpypi`: it runs after TestPyPI when both are selected.
- [ ] (`require_node` is removed.) Validate `Color` components and names; check `to_svg`/`to_tikz` results; reject unknown `GraphAttributes` flag bits.
- [ ] Unify `shortest_paths` / `min_st_cut` argument order, `directed` default and weight types.
- [ ] `compare_layouts` ranking handles NaN stress; fix `aspect_ratio` docstring.
- [ ] `from_networkx` overloads on `Literal`; warn when `label_attribute` is ignored; reject string edge pairs in `from_edges`.
- [ ] Weak tests: facade default, setter test, generator postconditions, `extension_path`.
- [x] Docs: Schnyder rejection reason, standalone fragments, duplicate `coverage.md` items.
- [ ] Make `_random.py:93` reachable in tests.
