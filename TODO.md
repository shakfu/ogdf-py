# TODO

IDs refer to findings in `REVIEW.md`.

## Critical

## High

## Medium

- [ ] Hidden edges (`HiddenEdgeSet`) are not in `Graph::edges` when a graph is destroyed, so their Python handles are not invalidated. No binding hides edges on a user graph today.

- [ ] A stale handle fails with nanobind's generic "incompatible function arguments" `TypeError`. A clearer message would need a check per access, which is what the tracker avoids.

- [ ] T4: `tests/test_safety.py` covers each critical class in-process, so a regression to a segfault aborts the whole run. Run them in subprocesses to report each crash separately. (seed=)` update `provenance()`.

- [ ] P8: `seeded()` does not replay the outer random stream on exit.

- [ ] P11: Dijkstra results do not treat `2**31-1` as the unreachable sentinel.

- [ ] C17: Release the GIL in layout and algorithm calls without Python callbacks. Calls that add or delete elements must keep it: `HandleTracker` (`errors.h`) calls into nanobind from OGDF's observer callbacks.

- [ ] B6: Add the runner image to OGDF cache keys (the wheel keys now include the cibuildwheel version and deployment target).

- [ ] B8: Pin GitHub Actions by SHA.

- [ ] T1 (rest): the other 44 untested exports.

- [ ] T2: Tests for layout setters with a measurable effect.

- [ ] T3: Strengthen the TikZ, bends and I/O round-trip tests.

## Low

- [ ] ruff and mypy cover `demos/`.

- [ ] (`require_node` is removed.) Validate `Color` components and names; check `to_svg`/`to_tikz` results; reject unknown `GraphAttributes` flag bits.

- [ ] Unify `shortest_paths` / `min_st_cut` argument order, `directed` default and weight types.

- [ ] `compare_layouts` ranking handles NaN stress; fix `aspect_ratio` docstring.

- [ ] `from_networkx` overloads on `Literal`; warn when `label_attribute` is ignored; reject string edge pairs in `from_edges`.

- [ ] Weak tests: facade default, setter test, generator postconditions, `extension_path`.

- [ ] Make `_random.py:93` reachable in tests.
