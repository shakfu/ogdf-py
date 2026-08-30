"""Seeding, provenance metadata, and heuristic objective values."""

import ogdf


def _random_layout(seed):
    with ogdf.seeded(seed):
        g = ogdf.Graph()
        ogdf.random_graph(g, 25, 50)
        ga = ogdf.GraphAttributes(g)
        ogdf.FMMMLayout().call(ga)
        return ogdf.to_edges(g), [(ga.x(v), ga.y(v)) for v in g.nodes()]


def test_same_seed_reproduces_graph_and_layout():
    assert _random_layout(20260831) == _random_layout(20260831)


def test_different_seeds_diverge():
    assert _random_layout(1) != _random_layout(2)


def test_set_seed_records_the_seed():
    assert ogdf.set_seed(1234) == 1234
    assert ogdf.get_seed() == 1234


def test_seeded_restores_the_previous_seed():
    ogdf.set_seed(11)
    with ogdf.seeded(22):
        assert ogdf.get_seed() == 22
    assert ogdf.get_seed() == 11


def test_new_seed_returns_an_int():
    assert isinstance(ogdf.new_seed(), int)


def test_provenance_records_seed_versions_and_settings():
    ogdf.set_seed(99)
    info = ogdf.provenance(algorithm="FMMMLayout", unit_edge_length=20.0)
    assert info["seed"] == 99
    assert info["package_version"] == ogdf.__version__
    assert info["ogdf_tag"]
    assert info["settings"] == {
        "algorithm": "FMMMLayout",
        "unit_edge_length": 20.0,
    }


def test_provenance_is_json_serializable():
    import json

    ogdf.set_seed(5)
    json.dumps(ogdf.provenance(algorithm="SugiyamaLayout", runs=4))


def test_heuristic_layouts_report_their_objective_value():
    g = ogdf.Graph()
    ogdf.complete_graph(g, 6)  # K6 has crossing number 3
    ga = ogdf.GraphAttributes(g)

    planarization = ogdf.PlanarizationLayout()
    planarization.call(ga)
    assert planarization.number_of_crossings() >= 3

    sugiyama = ogdf.SugiyamaLayout()
    sugiyama.call(ga)
    assert sugiyama.number_of_crossings() >= 0
    assert sugiyama.number_of_levels() > 0
