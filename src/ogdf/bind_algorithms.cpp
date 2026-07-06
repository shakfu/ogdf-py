// Core graph algorithms: connectivity, components, shortest paths, spanning
// trees, flow, cut, matching, coloring, planarity.
//
// Algorithms that produce per-node / per-edge results follow OGDF's idiom: the
// caller passes a NodeArray*/EdgeArray* output object, and the function returns
// the scalar result (a count, weight, or flow value).

#include "bindings.h"

#include <nanobind/stl/string.h>

#include <stdexcept>
#include <unordered_map>
#include <unordered_set>

#include <ogdf/basic/Graph.h>
#include <ogdf/basic/List.h>
#include <ogdf/basic/extended_graph_alg.h>
#include <ogdf/basic/simple_graph_alg.h>
#include <ogdf/decomposition/StaticSPQRTree.h>
#include <ogdf/graphalg/Dijkstra.h>
#include <ogdf/graphalg/Matching.h>
#include <ogdf/graphalg/MatchingBlossomV.h>
#include <ogdf/graphalg/MaxFlowGoldbergTarjan.h>
#include <ogdf/graphalg/MinCostFlowReinelt.h>
#include <ogdf/graphalg/MinSteinerTreeMehlhorn.h>
#include <ogdf/graphalg/MinimumCutStoerWagner.h>
#include <ogdf/graphalg/NodeColoringRecursiveLargestFirst.h>
#include <ogdf/graphalg/ShortestPathAlgorithms.h>
#include <ogdf/planarity/MaximalPlanarSubgraphSimple.h>
#include <ogdf/graphalg/ShortestPathWithBFM.h>
#include <ogdf/graphalg/steiner_tree/EdgeWeightedGraph.h>
#include <ogdf/graphalg/steiner_tree/EdgeWeightedGraphCopy.h>

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
    m.def("is_two_edge_connected",
          [](const Graph& g) { return isTwoEdgeConnected(g); }, "graph"_a,
          "True if the graph is 2-edge-connected (connected and bridgeless).");
    m.def("is_arborescence",
          [](const Graph& g) { return isArborescence(g); }, "graph"_a,
          "True if the graph is an arborescence (a rooted directed tree).");
    m.def("is_regular", [](const Graph& g) { return isRegular(g); }, "graph"_a,
          "True if every node has the same degree.");
    m.def("is_regular", [](const Graph& g, int d) { return isRegular(g, d); },
          "graph"_a, "degree"_a, "True if every node has degree d.");

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
    m.def("triangulate", &triangulate, "graph"_a,
          "Triangulate a simple, connected, planar embedded graph in place "
          "(call planar_embed first).");
    m.def("make_bimodal", [](Graph& g) { makeBimodal(g); }, "graph"_a,
          "Make a digraph bimodal by splitting nodes so in- and out-edges are "
          "contiguous, in place.");
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
    m.def("bfs_distances",
          [](const Graph& g, node source, NodeArray<int>& distance) {
              bfs_SPSS<int>(source, g, distance, 1);
          },
          "graph"_a, "source"_a, "distance"_a,
          "Unweighted single-source distances (edge hops) via BFS; writes the "
          "hop count to each node into `distance`.");

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

    // ---------------------------------------------------------------- //
    // Cut vertices and bridges                                         //
    // ---------------------------------------------------------------- //
    m.def("cut_vertices",
          [](const Graph& g) {
              ArrayBuffer<node> cut;
              findCutVertices(g, cut);
              nb::list out;
              for (node v : cut) {
                  out.append(nb::cast(v, nb::rv_policy::reference));
              }
              return out;
          },
          "graph"_a,
          "Return the cut vertices (articulation points) as a list of nodes. "
          "The graph should be connected.");
    m.def("bridges",
          [](const Graph& g) {
              // A bridge is an edge that is the only member of its biconnected
              // component (OGDF has no dedicated bridge finder).
              EdgeArray<int> component(g);
              biconnectedComponents(g, component);
              std::unordered_map<int, int> count;
              for (edge e : g.edges) {
                  ++count[component[e]];
              }
              nb::list out;
              for (edge e : g.edges) {
                  if (!e->isSelfLoop() && count[component[e]] == 1) {
                      out.append(nb::cast(e, nb::rv_policy::reference));
                  }
              }
              return out;
          },
          "graph"_a, "Return the bridge edges as a list.");

    // ---------------------------------------------------------------- //
    // Bellman-Ford (negative weights allowed)                          //
    // ---------------------------------------------------------------- //
    m.def("bellman_ford",
          [](const Graph& g, node source, const EdgeArray<int>& length,
             NodeArray<int>& distance) {
              NodeArray<edge> predecessor(g);
              return ShortestPathWithBFM().call(g, source, length, distance,
                                                predecessor);
          },
          "graph"_a, "source"_a, "length"_a, "distance"_a,
          "Bellman-Ford single-source shortest paths on a directed graph with "
          "integer (possibly negative) edge lengths. Returns False if a "
          "negative cycle exists; writes distances into `distance`.");

    // ---------------------------------------------------------------- //
    // General maximum-weight matching (Blossom V)                      //
    // ---------------------------------------------------------------- //
    m.def("maximum_weight_matching",
          [](const Graph& g, const EdgeArray<double>& weight,
             EdgeArray<bool>& matching) {
              std::unordered_set<edge> matched;
              MatchingBlossomV<double>().maximumWeightMatching(g, weight,
                                                               matched);
              matching.fill(false);
              double total = 0.0;
              for (edge e : matched) {
                  matching[e] = true;
                  total += weight[e];
              }
              return total;
          },
          "graph"_a, "weight"_a, "matching"_a,
          "Maximum-weight general matching (Blossom V). Returns the total "
          "weight; marks matched edges in `matching`.");

    // ---------------------------------------------------------------- //
    // Minimum-cost flow                                                //
    // ---------------------------------------------------------------- //
    m.def("min_cost_flow",
          [](const Graph& g, const EdgeArray<int>& lower_bound,
             const EdgeArray<int>& upper_bound, const EdgeArray<double>& cost,
             const NodeArray<int>& supply, EdgeArray<int>& flow) {
              return MinCostFlowReinelt<double>().call(
                  g, lower_bound, upper_bound, cost, supply, flow);
          },
          "graph"_a, "lower_bound"_a, "upper_bound"_a, "cost"_a, "supply"_a,
          "flow"_a,
          "Minimum-cost flow (Reinelt). Bounds, supply, and flow are integers; "
          "cost is a float. Node supply is positive for sources and negative "
          "for sinks and must sum to zero. Returns False if infeasible; writes "
          "per-edge flow into `flow`.");

    // ---------------------------------------------------------------- //
    // Minimum Steiner tree                                             //
    // ---------------------------------------------------------------- //
    m.def("steiner_tree",
          [](const Graph& g, const EdgeArray<double>& weight,
             nb::list terminals) {
              // Mirror the input into an EdgeWeightedGraph, tracking the map
              // back to the caller's edges so the result can be reported in
              // terms of the original graph.
              EdgeWeightedGraph<double> ewg;
              NodeArray<node> to_ewg(g, nullptr);
              std::unordered_map<edge, edge> to_user_edge;
              for (node v : g.nodes) {
                  to_ewg[v] = ewg.newNode();
              }
              for (edge e : g.edges) {
                  edge e2 = ewg.newEdge(to_ewg[e->source()],
                                        to_ewg[e->target()], weight[e]);
                  to_user_edge[e2] = e;
              }

              List<node> terms;
              NodeArray<bool> is_terminal(ewg, false);
              for (auto handle : terminals) {
                  node v2 = to_ewg[nb::cast<node>(handle)];
                  if (!is_terminal[v2]) {
                      is_terminal[v2] = true;
                      terms.pushBack(v2);
                  }
              }

              EdgeWeightedGraphCopy<double>* tree = nullptr;
              double total = MinSteinerTreeMehlhorn<double>().call(
                  ewg, terms, is_terminal, tree);

              nb::list edges;
              if (tree != nullptr) {
                  for (edge te : tree->edges) {
                      edge ewg_edge = tree->original(te);
                      if (ewg_edge != nullptr) {
                          edges.append(nb::cast(to_user_edge[ewg_edge],
                                                nb::rv_policy::reference));
                      }
                  }
                  delete tree;
              }
              return nb::make_tuple(total, edges);
          },
          "graph"_a, "weight"_a, "terminals"_a,
          "Minimum Steiner tree (Mehlhorn) connecting the given terminal "
          "nodes. Returns (total_weight, [tree_edges]).");

    // ---------------------------------------------------------------- //
    // Maximal planar subgraph                                          //
    // ---------------------------------------------------------------- //
    m.def("maximal_planar_subgraph",
          [](const Graph& g) {
              List<edge> del_edges;
              MaximalPlanarSubgraphSimple<int>().call(g, del_edges);
              nb::list out;
              for (edge e : del_edges) {
                  out.append(nb::cast(e, nb::rv_policy::reference));
              }
              return out;
          },
          "graph"_a,
          "Return the edges removed to obtain a maximal planar subgraph. An "
          "empty list means the graph is already planar.");

    // ---------------------------------------------------------------- //
    // Triconnectivity / SPQR                                           //
    // ---------------------------------------------------------------- //
    m.def("separation_pair",
          [](const Graph& g) -> nb::object {
              node s1 = nullptr;
              node s2 = nullptr;
              isTriconnected(g, s1, s2);
              if (s1 != nullptr && s2 != nullptr) {
                  return nb::make_tuple(
                      nb::cast(s1, nb::rv_policy::reference),
                      nb::cast(s2, nb::rv_policy::reference));
              }
              return nb::none();
          },
          "graph"_a,
          "Return one separation pair (2-cut) as (node, node) for a "
          "biconnected but not triconnected graph, or None if the graph is "
          "triconnected.");
    m.def("spqr_tree_summary",
          [](const Graph& g) {
              if (!isBiconnected(g) || g.numberOfNodes() < 3) {
                  throw std::invalid_argument(
                      "spqr_tree_summary requires a biconnected graph with at "
                      "least 3 nodes");
              }
              StaticSPQRTree tree(g);
              nb::dict summary;
              summary["S"] = tree.numberOfSNodes();  // series (polygon)
              summary["P"] = tree.numberOfPNodes();  // parallel (bond)
              summary["R"] = tree.numberOfRNodes();  // rigid (triconnected)
              summary["nodes"] = tree.tree().numberOfNodes();
              return summary;
          },
          "graph"_a,
          "SPQR-tree node counts for a biconnected graph (>= 3 nodes): S "
          "(series), P (parallel), and R (rigid/triconnected) nodes, plus the "
          "total number of tree nodes.");
}
