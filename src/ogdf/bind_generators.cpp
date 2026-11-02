// Graph generators.

#include "bindings.h"
#include "errors.h"

#include <nanobind/stl/vector.h>

#include <cmath>
#include <string>
#include <vector>

#include <ogdf/basic/Array.h>
#include <ogdf/basic/graph_generators/deterministic.h>
#include <ogdf/basic/graph_generators/operations.h>
#include <ogdf/basic/graph_generators/randomized.h>

using namespace ogdf;
using namespace nb::literals;

namespace {

// Convert a Python list of ints to an ogdf::Array<int>.
Array<int> to_array(const std::vector<int>& values) {
    Array<int> arr(static_cast<int>(values.size()));
    for (int i = 0; i < static_cast<int>(values.size()); ++i) {
        arr[i] = values[i];
    }
    return arr;
}

using ogdfpy::require_arg;

void require_count(int value, int minimum, const char* op, const char* arg) {
    require_arg(value >= minimum, op,
                std::string(arg) + " must be >= " + std::to_string(minimum));
}

void require_probability(double p, const char* op, const char* arg) {
    require_arg(p >= 0.0 && p <= 1.0, op,
                std::string(arg) + " must be in [0, 1]");
}

}  // namespace

void register_generators(nb::module_& m) {
    // --- deterministic --- //
    m.def("complete_graph",
          [](Graph& g, int n) {
              require_count(n, 0, "complete_graph", "n");
              completeGraph(g, n);
          },
          "graph"_a, "n"_a,
          "Complete graph on n nodes.");
    m.def("complete_bipartite_graph",
          [](Graph& g, int n, int mm) {
              require_count(n, 0, "complete_bipartite_graph", "n");
              require_count(mm, 0, "complete_bipartite_graph", "m");
              completeBipartiteGraph(g, n, mm);
          },
          "graph"_a, "n"_a, "m"_a, "Complete bipartite graph K(n,m).");
    m.def("wheel_graph",
          [](Graph& g, int n) {
              require_count(n, 2, "wheel_graph", "n");
              wheelGraph(g, n);
          },
          "graph"_a, "n"_a,
          "Wheel graph: a cycle of n nodes plus a hub.");
    // 1 << n overflows int for n >= 31.
    m.def("cube_graph",
          [](Graph& g, int n) {
              require_arg(n >= 0 && n <= 30, "cube_graph",
                          "n must be in [0, 30]");
              cubeGraph(g, n);
          },
          "graph"_a, "n"_a,
          "n-dimensional hypercube graph.");
    m.def("grid_graph",
          [](Graph& g, int n, int mm, bool loop_n, bool loop_m) {
              require_count(n, 0, "grid_graph", "n");
              require_count(mm, 0, "grid_graph", "m");
              require_arg(!(loop_n || loop_m) || (n >= 1 && mm >= 1),
                          "grid_graph",
                          "a toroidal grid needs n >= 1 and m >= 1");
              gridGraph(g, n, mm, loop_n, loop_m);
          },
          "graph"_a, "n"_a, "m"_a, "loop_n"_a = false, "loop_m"_a = false,
          "n x m grid graph (optionally toroidal in each dimension).");
    m.def("petersen_graph",
          [](Graph& g, int n, int mm) {
              require_count(n, 3, "petersen_graph", "n");
              require_arg(mm >= 1 && 2 * mm < n, "petersen_graph",
                          "m must satisfy 1 <= m < n / 2");
              petersenGraph(g, n, mm);
          },
          "graph"_a, "n"_a = 5, "m"_a = 2, "Generalized Petersen graph.");
    m.def("regular_tree",
          [](Graph& g, int n, int children) {
              require_count(n, 0, "regular_tree", "n");
              require_count(children, 1, "regular_tree", "children");
              regularTree(g, n, children);
          },
          "graph"_a, "n"_a, "children"_a,
          "Rooted tree with n nodes where each has `children` children.");
    m.def("empty_graph",
          [](Graph& g, int nodes) {
              require_count(nodes, 0, "empty_graph", "nodes");
              emptyGraph(g, nodes);
          },
          "graph"_a, "nodes"_a,
          "Graph with the given number of isolated nodes.");

    // --- random --- //
    m.def("random_graph",
          [](Graph& g, int n, int edges) {
              require_count(n, 0, "random_graph", "nodes");
              require_count(edges, 0, "random_graph", "edges");
              require_arg(n > 0 || edges == 0, "random_graph",
                          "edges require at least one node");
              randomGraph(g, n, edges);
          },
          "graph"_a, "nodes"_a, "edges"_a,
          "Random graph with n nodes and m edges.");
    m.def("random_tree",
          [](Graph& g, int n) {
              require_count(n, 0, "random_tree", "nodes");
              randomTree(g, n);
          },
          "graph"_a, "nodes"_a, "Random tree with n nodes.");
    m.def("random_digraph",
          [](Graph& g, int n, double p) {
              require_count(n, 0, "random_digraph", "nodes");
              require_probability(p, "random_digraph", "edge_probability");
              randomDigraph(g, n, p);
          },
          "graph"_a, "nodes"_a, "edge_probability"_a,
          "Random digraph on n nodes; each arc present with probability p.");
    m.def("random_regular_graph",
          [](Graph& g, int n, int d) {
              // An impossible (n, d) makes OGDF retry forever.
              require_count(n, 0, "random_regular_graph", "nodes");
              require_arg(d >= 0 && (n == 0 || d < n), "random_regular_graph",
                          "degree must satisfy 0 <= degree < nodes");
              require_arg((static_cast<long long>(n) * d) % 2 == 0,
                          "random_regular_graph",
                          "nodes * degree must be even");
              randomRegularGraph(g, n, d);
          },
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
    m.def("random_planar_biconnected_graph",
          [](Graph& g, int n, int m2, bool multi_edges) {
              randomPlanarBiconnectedGraph(g, n, m2, multi_edges);
          },
          "graph"_a, "nodes"_a, "edges"_a, "multi_edges"_a = false,
          "Random planar biconnected graph.");
    m.def("random_planar_triconnected_graph",
          [](Graph& g, int n, int m2) {
              randomPlanarTriconnectedGraph(g, n, m2);
          },
          "graph"_a, "nodes"_a, "edges"_a,
          "Random planar triconnected graph.");
    m.def("random_triconnected_graph", &randomTriconnectedGraph, "graph"_a,
          "nodes"_a, "p1"_a, "p2"_a,
          "Random triconnected graph (p1, p2 tune the composition).");
    m.def("preferential_attachment_graph", &preferentialAttachmentGraph,
          "graph"_a, "nodes"_a, "min_degree"_a,
          "Barabasi-Albert preferential-attachment graph.");
    m.def("random_watts_strogatz_graph",
          [](Graph& g, int n, int k, double p) {
              const char* op = "random_watts_strogatz_graph";
              require_count(n, 0, op, "n");
              require_arg(k >= 0 && k % 2 == 0 && 2 * k < n, op,
                          "k must be even, >= 0 and smaller than n / 2");
              require_probability(p, op, "probability");
              randomWattsStrogatzGraph(g, n, k, p);
          },
          "graph"_a, "n"_a, "k"_a, "probability"_a,
          "Watts-Strogatz small-world graph (ring of degree k, rewired with "
          "the given probability).");
    m.def("random_chung_lu_graph",
          [](Graph& g, const std::vector<int>& expected_degrees) {
              randomChungLuGraph(g, to_array(expected_degrees));
          },
          "graph"_a, "expected_degrees"_a,
          "Chung-Lu random graph with the given expected degree sequence.");
    m.def("random_waxman_graph",
          [](Graph& g, int nodes, double alpha, double beta, double width,
             double height) {
              randomWaxmanGraph(g, nodes, alpha, beta, width, height);
          },
          "graph"_a, "nodes"_a, "alpha"_a, "beta"_a, "width"_a = 1.0,
          "height"_a = 1.0, "Waxman random geometric graph.");
    m.def("random_geometric_cube_graph",
          [](Graph& g, int nodes, double threshold, int dimension) {
              randomGeometricCubeGraph(g, nodes, threshold, dimension);
          },
          "graph"_a, "nodes"_a, "threshold"_a, "dimension"_a = 2,
          "Random geometric graph: points in a unit cube joined within "
          "`threshold` distance.");
    m.def("random_hierarchy",
          [](Graph& g, int n, int mm, bool planar, bool single_source,
             bool long_edges) {
              require_count(n, 0, "random_hierarchy", "n");
              require_count(mm, 0, "random_hierarchy", "m");
              randomHierarchy(g, n, mm, planar, single_source, long_edges);
          },
          "graph"_a, "n"_a, "m"_a,
          "planar"_a, "single_source"_a, "long_edges"_a,
          "Random layered hierarchy with n nodes and m edges.");
    m.def("random_series_parallel_dag",
          [](Graph& g, int edges, double p, double flt) {
              const char* op = "random_series_parallel_dag";
              require_count(edges, 1, op, "edges");
              require_probability(p, op, "randomness");
              require_arg(flt >= 0.0 && flt < 1.0, op, "flt must be in [0, 1)");
              randomSeriesParallelDAG(g, edges, p, flt);
          },
          "graph"_a, "edges"_a, "randomness"_a = 0.5, "flt"_a = 0.0,
          "Random series-parallel DAG.");

    // --- deterministic (additional) --- //
    m.def("circulant_graph",
          [](Graph& g, int n, const std::vector<int>& jumps) {
              circulantGraph(g, n, to_array(jumps));
          },
          "graph"_a, "n"_a, "jumps"_a,
          "Circulant graph on n nodes with the given jump set.");
    m.def("complete_kpartite_graph",
          [](Graph& g, const std::vector<int>& part_sizes) {
              completeKPartiteGraph(g, to_array(part_sizes));
          },
          "graph"_a, "part_sizes"_a,
          "Complete k-partite graph with the given part sizes.");
    m.def("globe_graph",
          [](Graph& g, int meridians, int latitudes) {
              require_count(meridians, 1, "globe_graph", "meridians");
              require_count(latitudes, 1, "globe_graph", "latitudes");
              globeGraph(g, meridians, latitudes);
          },
          "graph"_a, "meridians"_a, "latitudes"_a,
          "Globe graph with the given meridians and latitudes.");
    m.def("regular_lattice_graph",
          [](Graph& g, int n, int k) {
              require_count(n, 4, "regular_lattice_graph", "n");
              require_arg(k >= 0 && k % 2 == 0 && k <= n - 2,
                          "regular_lattice_graph",
                          "k must be even and in [0, n - 2]");
              regularLatticeGraph(g, n, k);
          },
          "graph"_a, "n"_a, "k"_a,
          "Regular lattice graph: a ring of n nodes each joined to its k "
          "nearest neighbours.");
    m.def("suspension",
          [](Graph& g, int s) {
              require_count(s, 0, "suspension", "s");
              suspension(g, s);
          },
          "graph"_a, "s"_a,
          "Add s suspension nodes, each joined to every existing node.");

    // --- operations --- //
    // graphUnion iterates graph2 while adding to graph1, so aliasing does not
    // terminate.
    m.def("graph_union",
          [](Graph& g1, const Graph& g2) {
              require_arg(&g1 != &g2, "graph_union",
                          "graph1 and graph2 must be different graphs");
              graphUnion(g1, g2);
          },
          "graph1"_a, "graph2"_a,
          "Merge graph2 into graph1 (disjoint union, in place).");
    m.def("complement",
          [](Graph& g, bool directed, bool allow_self_loops) {
              complement(g, directed, allow_self_loops);
          },
          "graph"_a, "directed"_a = false, "allow_self_loops"_a = false,
          "Replace the graph with its complement, in place.");

    auto product = [&m](const char* name,
                        void (*fn)(const Graph&, const Graph&, Graph&,
                                   NodeArray<NodeArray<node>>&),
                        const char* doc) {
        m.def(name,
              [fn, name](const Graph& g1, const Graph& g2, Graph& out) {
                  // `product` is cleared first, so it must not be an input.
                  require_arg(&out != &g1 && &out != &g2, name,
                              "product must be a different graph from the "
                              "inputs");
                  NodeArray<NodeArray<node>> node_map;
                  fn(g1, g2, out, node_map);
              },
              "graph1"_a, "graph2"_a, "product"_a, doc);
    };
    product("cartesian_product", &cartesianProduct,
            "Cartesian product of two graphs, written into `product`.");
    product("tensor_product", &tensorProduct,
            "Tensor (categorical) product, written into `product`.");
    product("strong_product", &strongProduct,
            "Strong product, written into `product`.");
    product("lexicographical_product", &lexicographicalProduct,
            "Lexicographical product, written into `product`.");
}
