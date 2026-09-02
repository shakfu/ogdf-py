"""Verify the concrete output values printed in the documentation.

Documentation that shows a result is a claim, and a claim nothing checks will
eventually be wrong - twice already: the `drawing_metrics` example in
`docs/metrics.md` was written by hand rather than measured, and the capability
counts in `docs/getting-started.md` went stale as more functions were bound.

These tests re-derive each documented value and compare. When one fails, the
documentation is out of date: rerun the snippet and paste in what it prints.
Values that depend on the standard library's random distributions are checked
for internal consistency instead of equality; see the metrics test.
"""

import ast
import math
import re
from pathlib import Path

import pytest

import ogdf

DOCS = Path(__file__).resolve().parent.parent / "docs"


def _read(name: str) -> str:
    path = DOCS / name
    if not path.exists():  # pragma: no cover - docs ship with the repo
        pytest.skip(f"{name} not present")
    return path.read_text()


def test_installation_report_capability_counts_are_current():
    text = _read("getting-started.md")
    match = re.search(
        r"capabilities\s+:\s*(\d+) layouts, (\d+) algorithms/generators, "
        r"(\d+) I/O functions, (\d+) types",
        text,
    )
    assert match, "the sample installation report is missing its capabilities line"
    documented = tuple(int(g) for g in match.groups())
    caps = ogdf.about()["capabilities"]
    actual = (caps["layouts"], caps["functions"], caps["io"], caps["types"])
    assert documented == actual, (
        f"docs/getting-started.md claims {documented} but ogdf.about() reports "
        f"{actual}; update the sample report"
    )


def test_layout_count_claimed_in_the_selection_guide():
    text = _read("choosing-a-layout.md")
    assert "nineteen layouts" in text
    assert len(ogdf.about()["capability_names"]["layouts"]) == 19


def test_drawing_metrics_example_matches_reality():
    """The dict printed in docs/metrics.md must describe what the snippet does.

    Only the portable part of that claim is checked. `random_graph` draws
    through `std::uniform_int_distribution`, whose algorithm the C++ standard
    leaves to the implementation, so the same seed builds a different graph
    under libstdc++ than under libc++ and every measured value moves with it.
    What holds everywhere is the key set, the graph size, and the arithmetic
    relating the documented numbers to each other - a stale block fails those
    as soon as a metric is added, renamed, or recomputed differently.
    """
    text = _read("metrics.md")
    block = re.search(r"\{'nodes': 40[^}]*\}", text, re.DOTALL)
    assert block, "the drawing_metrics example block is missing"
    documented = ast.literal_eval(block.group(0))

    g = ogdf.Graph()
    with ogdf.seeded(1):
        ogdf.random_graph(g, 40, 80)
    ga = ogdf.GraphAttributes(g)
    ogdf.FMMMLayout().call(ga)
    actual = ogdf.drawing_metrics(ga)

    assert set(documented) == set(actual), "the documented keys are out of date"
    for key, value in documented.items():
        assert type(value) is type(actual[key]), key
    assert documented["nodes"] == actual["nodes"]
    assert documented["edges"] == actual["edges"]

    width, height = documented["width"], documented["height"]
    assert documented["area"] == pytest.approx(width * height, rel=1e-3)
    assert documented["aspect_ratio"] == pytest.approx(
        max(width, height) / min(width, height), abs=1e-3
    )
    assert (
        documented["edge_length_min"]
        <= documented["edge_length_mean"]
        <= documented["edge_length_max"]
    )
    assert documented["edge_length_cv"] == pytest.approx(
        documented["edge_length_stdev"] / documented["edge_length_mean"], abs=1e-3
    )
    assert documented["min_angle_degrees"] == pytest.approx(
        math.degrees(documented["min_angle"]), abs=1e-3
    )


def test_recipe_build_order_is_what_the_recipe_prints():
    text = _read("recipes.md")
    match = re.search(r"# (\['crypto'.*?\])", text)
    assert match, "the build-order comment is missing from the DAG recipe"
    documented = ast.literal_eval(match.group(1))

    dependencies = [
        ("app", "http"),
        ("app", "db"),
        ("http", "tls"),
        ("http", "sockets"),
        ("db", "sockets"),
        ("tls", "crypto"),
    ]
    g, mapping = ogdf.from_edges(dependencies)
    order = ogdf.NodeArrayInt(g)
    ogdf.topological_numbering(g, order)
    keys = {v: k for k, v in mapping.items()}
    actual = [keys[v] for v in sorted(g.nodes(), key=lambda v: order[v], reverse=True)]
    assert documented == actual


def test_small_inline_claims():
    """The `# result` comments scattered through the getting-started guide."""
    text = _read("getting-started.md")

    # print(g.number_of_nodes(), g.number_of_edges())   # 3 2
    assert "# 3 2" in text
    g = ogdf.Graph()
    a, b, c = g.new_node(), g.new_node(), g.new_node()
    g.new_edge(a, b)
    g.new_edge(b, c)
    assert (g.number_of_nodes(), g.number_of_edges()) == (3, 2)

    # ogdf.to_edges(g, keys=keys)  # [('a', 'b'), ('b', 'c'), ('c', 'a')]
    assert "# [('a', 'b'), ('b', 'c'), ('c', 'a')]" in text
    h, mapping = ogdf.from_edges([("a", "b"), ("b", "c"), ("c", "a")])
    keys = {v: k for k, v in mapping.items()}
    assert ogdf.to_edges(h, keys=keys) == [("a", "b"), ("b", "c"), ("c", "a")]

    # requirements / validate / is_valid_for on K5
    assert "# ('at least 3 nodes', 'planar', 'triconnected')" in text
    k5 = ogdf.Graph()
    ogdf.complete_graph(k5, 5)
    assert ogdf.requirements("TutteLayout") == (
        "at least 3 nodes",
        "planar",
        "triconnected",
    )
    assert ogdf.validate("TutteLayout", k5) == ["planar"]
    assert ogdf.is_valid_for("TutteLayout", k5) is False


def test_provenance_example_keys_match():
    text = _read("getting-started.md")
    match = re.search(r"\{'seed': 42.*?\}\}", text, re.DOTALL)
    assert match, "the provenance example is missing"
    documented = ast.literal_eval(match.group(0))

    ogdf.set_seed(42)
    actual = ogdf.provenance(algorithm="FMMMLayout", unit_edge_length=20.0)
    # Platform, machine and interpreter version legitimately differ per machine;
    # everything else is a fact about the package.
    for key in ("seed", "package_version", "ogdf_version", "ogdf_tag", "settings"):
        assert documented[key] == actual[key], key
    assert set(documented) == set(actual)
