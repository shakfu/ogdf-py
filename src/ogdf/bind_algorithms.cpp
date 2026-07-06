// Core graph algorithms: connectivity, components, shortest paths, spanning
// trees, flow, cut, matching, coloring, planarity.
//
// Algorithms that produce per-node / per-edge results follow OGDF's idiom: the
// caller passes a NodeArray*/EdgeArray* output object, and the function returns
// the scalar result (a count, weight, or flow value).

#include "bindings.h"

#include <nanobind/stl/string.h>

#include <stdexcept>

#include <ogdf/basic/Graph.h>
#include <ogdf/basic/List.h>
#include <ogdf/basic/extended_graph_alg.h>
#include <ogdf/basic/simple_graph_alg.h>
#include <ogdf/graphalg/Dijkstra.h>
#include <ogdf/graphalg/Matching.h>
#include <ogdf/graphalg/MaxFlowGoldbergTarjan.h>
#include <ogdf/graphalg/MinimumCutStoerWagner.h>
#include <ogdf/graphalg/NodeColoringRecursiveLargestFirst.h>

using namespace ogdf;
using namespace nb::literals;

void register_algorithms(nb::module_& m) {
    // ---------------------------------------------------------------- //
    // Connectivity predicates                                          //
    // ---------------------------------------------------------------- //
    m.def("is_connected", &isConnected, "graph"_a);
    m.def("is_biconnected",
          [](const Graph& g) { return isBiconnected(g); }, "graph"_a);
    m.def("is_triconnected",
          [](const Graph& g) { return isTriconnected(g); }, "graph"_a);
    m.def("is_acyclic", [](const Graph& g) { return isAcyclic(g); }, "graph"_a,
          "True if the directed graph is acyclic.");
    m.def("is_acyclic_undirected",
          [](const Graph& g) { return isAcyclicUndirected(g); }, "graph"_a);
    m.def("is_bipartite", [](const Graph& g) { return isBipartite(g); },
          "graph"_a);
    m.def("is_bipartite",
          [](const Graph& g, NodeArray<bool>& coloring) {
              return isBipartite(g, coloring);
          },
          "graph"_a, "coloring"_a,
          "True if bipartite; writes a 2-coloring into `coloring`.");
    m.def("is_tree", &isTree, "graph"_a);
    m.def("is_forest", [](const Graph& g) { return isForest(g); }, "graph"_a);
    m.def("is_planar", &isPlanar, "graph"_a);

    // ---------------------------------------------------------------- //
    // Components (return count; write ids into the output array)        //
    // ---------------------------------------------------------------- //
    m.def("connected_components",
          [](const Graph& g, NodeArray<int>& component) {
              return connectedComponents(g, component);
          },
          "graph"_a, "component"_a,
          "Number of connected components; writes each node's id into "
          "`component`.");
    m.def("strong_components",
          [](const Graph& g, NodeArray<int>& component) {
              return strongComponents(g, component);
          },
          "graph"_a, "component"_a,
          "Number of strongly connected components (node ids into "
          "`component`).");
    m.def("biconnected_components",
          [](const Graph& g, EdgeArray<int>& component) {
              return biconnectedComponents(g, component);
          },
          "graph"_a, "component"_a,
          "Number of biconnected components; writes each edge's id into "
          "`component`.");
    m.def("topological_numbering",
          [](const Graph& g, NodeArray<int>& num) {
              topologicalNumbering(g, num);
          },
          "graph"_a, "numbering"_a,
          "Write a topological numbering of a DAG into `numbering`.");

    // ---------------------------------------------------------------- //
    // Mutators / embedding                                             //
    // ---------------------------------------------------------------- //
    m.def("make_connected", [](Graph& g) { makeConnected(g); }, "graph"_a,
          "Add edges to make the graph connected.");
    m.def("make_biconnected", [](Graph& g) { makeBiconnected(g); }, "graph"_a,
          "Add edges to make the graph biconnected.");
    m.def("make_acyclic", &makeAcyclic, "graph"_a,
          "Remove edges to make the directed graph acyclic.");
    m.def("planar_embed", &planarEmbed, "graph"_a,
          "Compute a planar embedding (reorders adjacency lists). Returns "
          "False if the graph is not planar.");
    m.def("planar_embed_planar_graph", &planarEmbedPlanarGraph, "graph"_a,
          "Faster planar embedding for a graph already known to be planar.");

    // ---------------------------------------------------------------- //
    // Shortest paths                                                   //
    // ---------------------------------------------------------------- //
    m.def("dijkstra",
          [](const Graph& g, const EdgeArray<double>& weight, node source,
             NodeArray<double>& distance, bool directed) {
              NodeArray<edge> predecessor(g);
              Dijkstra<double>().call(g, weight, source, predecessor, distance,
                                      directed);
          },
          "graph"_a, "weight"_a, "source"_a, "distance"_a,
          "directed"_a = false,
          "Single-source shortest paths; writes distances into `distance`.");

    // ---------------------------------------------------------------- //
    // Minimum spanning tree                                            //
    // ---------------------------------------------------------------- //
    m.def("min_spanning_tree",
          [](const Graph& g, const EdgeArray<double>& weight,
             EdgeArray<bool>& in_tree) {
              return computeMinST(g, weight, in_tree);
          },
          "graph"_a, "weight"_a, "in_tree"_a,
          "Minimum spanning tree (Prim). Returns total weight; marks tree "
          "edges in `in_tree`. Does not modify the graph.");
    m.def("make_minimum_spanning_tree",
          [](Graph& g, const EdgeArray<double>& weight) {
              return makeMinimumSpanningTree(g, weight);
          },
          "graph"_a, "weight"_a,
          "Reduce the graph in place to its minimum spanning tree (Kruskal). "
          "Returns total weight.");

    // ---------------------------------------------------------------- //
    // Max flow / min cut                                               //
    // ---------------------------------------------------------------- //
    m.def("max_flow",
          [](const Graph& g, const EdgeArray<double>& capacity, node s,
             node t, EdgeArray<double>& flow) {
              EdgeArray<double> cap(capacity);  // computeFlow needs non-const
              MaxFlowGoldbergTarjan<double> mf(g);
              return mf.computeFlow(cap, s, t, flow);
          },
          "graph"_a, "capacity"_a, "source"_a, "sink"_a, "flow"_a,
          "Maximum s-t flow (Goldberg-Tarjan). Returns the flow value; writes "
          "per-edge flow into `flow`.");
    m.def("min_cut",
          [](const Graph& g, const EdgeArray<double>& weight) {
              MinimumCutStoerWagner<double> mc;
              return mc.call(g, weight);
          },
          "graph"_a, "weight"_a,
          "Global minimum cut value (Stoer-Wagner) for an undirected weighted "
          "graph.");

    // ---------------------------------------------------------------- //
    // Matching                                                         //
    // ---------------------------------------------------------------- //
    m.def("maximal_matching",
          [](const Graph& g) {
              ArrayBuffer<edge> matching;
              Matching::findMaximalMatching(g, matching);
              nb::list out;
              for (edge e : matching) {
                  out.append(nb::cast(e, nb::rv_policy::reference));
              }
              return out;
          },
          "graph"_a, "Return a maximal matching as a list of edges.");
    m.def("maximum_matching_bipartite",
          [](const Graph& g, EdgeArray<bool>& matching) {
              NodeArray<bool> color(g);
              if (!isBipartite(g, color)) {
                  throw std::runtime_error("graph is not bipartite");
              }
              List<node> U, V;
              for (node v : g.nodes) {
                  (color[v] ? V : U).pushBack(v);
              }
              Matching::findMaximumCardinalityMatching(g, U, V, matching);
              // Count matched edges directly: the returned int is not a
              // reliable cardinality, but the output array is authoritative.
              int size = 0;
              for (edge e : g.edges) {
                  if (matching[e]) {
                      ++size;
                  }
              }
              return size;
          },
          "graph"_a, "matching"_a,
          "Maximum-cardinality matching of a bipartite graph (the bipartition "
          "is computed automatically). Returns its size; marks matched edges "
          "in `matching`. Raises if the graph is not bipartite.");

    // ---------------------------------------------------------------- //
    // Node coloring                                                    //
    // ---------------------------------------------------------------- //
    m.def("node_coloring",
          [](const Graph& g, NodeArray<int>& colors) {
              NodeArray<NodeColoringModule::NodeColor> tmp(g);
              auto k = NodeColoringRecursiveLargestFirst().call(g, tmp);
              for (node v : g.nodes) {
                  colors[v] = static_cast<int>(tmp[v]);
              }
              return static_cast<int>(k);
          },
          "graph"_a, "colors"_a,
          "Heuristic proper node coloring (Recursive Largest First). Returns "
          "the number of colors; writes each node's color into `colors`.");
}
