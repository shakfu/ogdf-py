// Graph generators.

#include "bindings.h"

#include <ogdf/basic/graph_generators/deterministic.h>
#include <ogdf/basic/graph_generators/randomized.h>

using namespace ogdf;
using namespace nb::literals;

void register_generators(nb::module_& m) {
    // --- deterministic --- //
    m.def("complete_graph", &completeGraph, "graph"_a, "n"_a,
          "Complete graph on n nodes.");
    m.def("complete_bipartite_graph", &completeBipartiteGraph, "graph"_a,
          "n"_a, "m"_a, "Complete bipartite graph K(n,m).");
    m.def("wheel_graph", &wheelGraph, "graph"_a, "n"_a,
          "Wheel graph: a cycle of n nodes plus a hub.");
    m.def("cube_graph", &cubeGraph, "graph"_a, "n"_a,
          "n-dimensional hypercube graph.");
    m.def("grid_graph",
          [](Graph& g, int n, int mm, bool loop_n, bool loop_m) {
              gridGraph(g, n, mm, loop_n, loop_m);
          },
          "graph"_a, "n"_a, "m"_a, "loop_n"_a = false, "loop_m"_a = false,
          "n x m grid graph (optionally toroidal in each dimension).");
    m.def("petersen_graph",
          [](Graph& g, int n, int mm) { petersenGraph(g, n, mm); },
          "graph"_a, "n"_a = 5, "m"_a = 2, "Generalized Petersen graph.");
    m.def("regular_tree", &regularTree, "graph"_a, "n"_a, "children"_a,
          "Rooted tree with n nodes where each has `children` children.");
    m.def("empty_graph", &emptyGraph, "graph"_a, "nodes"_a,
          "Graph with the given number of isolated nodes.");

    // --- random --- //
    m.def("random_graph",
          [](Graph& g, int n, int edges) { randomGraph(g, n, edges); },
          "graph"_a, "nodes"_a, "edges"_a,
          "Random graph with n nodes and m edges.");
    m.def("random_tree", [](Graph& g, int n) { randomTree(g, n); },
          "graph"_a, "nodes"_a, "Random tree with n nodes.");
    m.def("random_digraph",
          [](Graph& g, int n, double p) { randomDigraph(g, n, p); },
          "graph"_a, "nodes"_a, "edge_probability"_a,
          "Random digraph on n nodes; each arc present with probability p.");
    m.def("random_regular_graph",
          [](Graph& g, int n, int d) { randomRegularGraph(g, n, d); },
          "graph"_a, "nodes"_a, "degree"_a,
          "Random d-regular graph on n nodes.");
    m.def("random_biconnected_graph",
          [](Graph& g, int n, int edges) {
              randomBiconnectedGraph(g, n, edges);
          },
          "graph"_a, "nodes"_a, "edges"_a,
          "Random biconnected graph with n nodes and m edges.");
    m.def("random_planar_connected_graph",
          [](Graph& g, int n, int edges) {
              randomPlanarConnectedGraph(g, n, edges);
          },
          "graph"_a, "nodes"_a, "edges"_a,
          "Random planar connected graph with n nodes and m edges.");
}
