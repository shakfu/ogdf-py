// Graph generators.

#include "bindings.h"

#include <nanobind/stl/vector.h>

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

}  // namespace

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
    m.def("random_watts_strogatz_graph", &randomWattsStrogatzGraph, "graph"_a,
          "n"_a, "k"_a, "probability"_a,
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
    m.def("random_hierarchy", &randomHierarchy, "graph"_a, "n"_a, "m"_a,
          "planar"_a, "single_source"_a, "long_edges"_a,
          "Random layered hierarchy with n nodes and m edges.");
    m.def("random_series_parallel_dag",
          [](Graph& g, int edges, double p, double flt) {
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
    m.def("globe_graph", &globeGraph, "graph"_a, "meridians"_a, "latitudes"_a,
          "Globe graph with the given meridians and latitudes.");
    m.def("regular_lattice_graph", &regularLatticeGraph, "graph"_a, "n"_a,
          "k"_a,
          "Regular lattice graph: a ring of n nodes each joined to its k "
          "nearest neighbours.");
    m.def("suspension", &suspension, "graph"_a, "s"_a,
          "Add s suspension nodes, each joined to every existing node.");

    // --- operations --- //
    m.def("graph_union", [](Graph& g1, const Graph& g2) { graphUnion(g1, g2); },
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
              [fn](const Graph& g1, const Graph& g2, Graph& out) {
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
