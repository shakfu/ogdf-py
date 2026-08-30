// Core graph algorithms: connectivity, components, shortest paths, spanning
// trees, flow, cut, matching, coloring, planarity.
//
// Algorithms that produce per-node / per-edge results follow OGDF's idiom: the
// caller passes a NodeArray*/EdgeArray* output object, and the function returns
// the scalar result (a count, weight, or flow value).

#include "bindings.h"
#include "errors.h"

#include <nanobind/stl/string.h>

#include <functional>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>

#include <ogdf/basic/Graph.h>
#include <ogdf/basic/List.h>
#include <ogdf/basic/extended_graph_alg.h>
#include <ogdf/basic/simple_graph_alg.h>
#include <ogdf/decomposition/StaticSPQRTree.h>
#include <ogdf/graphalg/AStarSearch.h>
#include <ogdf/graphalg/ConnectivityTester.h>
#include <ogdf/graphalg/Dijkstra.h>
#include <ogdf/graphalg/MinSTCutMaxFlow.h>
#include <ogdf/graphalg/Matching.h>
#include <ogdf/graphalg/MatchingBlossomV.h>
#include <ogdf/graphalg/MaxFlowGoldbergTarjan.h>
#include <ogdf/graphalg/MinCostFlowReinelt.h>
#include <ogdf/graphalg/MinSteinerTreeMehlhorn.h>
#include <ogdf/graphalg/MinimumCutStoerWagner.h>
#include <ogdf/graphalg/NodeColoringRecursiveLargestFirst.h>
#include <ogdf/graphalg/ShortestPathAlgorithms.h>
#include <ogdf/planarity/MaximalPlanarSubgraphSimple.h>
#include <ogdf/planarity/PlanRep.h>
#include <ogdf/planarity/PlanRepLight.h>
#include <ogdf/planarity/SubgraphPlanarizer.h>
#include <ogdf/planarity/VariableEmbeddingInserter.h>
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
    m.def("is_simple", [](const Graph& g) { return isSimple(g); }, "graph"_a,
          "True if the graph has no self-loops and no parallel edges, where a "
          "pair of opposite directed edges counts as parallel only if it "
          "repeats the same direction. See `is_simple_undirected` for the "
          "stricter undirected notion used by the planar layouts.");
    m.def("is_simple_undirected",
          [](const Graph& g) { return isSimpleUndirected(g); }, "graph"_a,
          "True if the graph is simple when edge direction is ignored: no "
          "self-loops, and at most one edge between any pair of nodes. This is "
          "the simplicity the planar grid layouts require.");
    m.def("has_self_loops",
          [](const Graph& g) {
              for (edge e : g.edges) {
                  if (e->isSelfLoop()) {
                      return true;
                  }
              }
              return false;
          },
          "graph"_a, "True if any edge connects a node to itself.");
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
    // k-connectivity (node / edge)                                     //
    // ---------------------------------------------------------------- //
    auto global_connectivity = [](const Graph& g, bool node_conn,
                                  bool directed) {
        if (g.numberOfNodes() < 2) {
            return 0;  // connectivity of the trivial graph is 0 by convention
        }
        NodeArray<NodeArray<int>> conn(g);
        for (node v : g.nodes) {
            conn[v].init(g);
        }
        ConnectivityTester ct(node_conn, directed);
        return ct.computeConnectivity(g, conn);
    };
    auto local_connectivity = [](const Graph& g, node s, node t, bool node_conn,
                                 bool directed) {
        ogdfpy::require_distinct(s, t, "connectivity");
        ConnectivityTester ct(node_conn, directed);
        return ct.computeConnectivity(g, s, t);
    };
    m.def("node_connectivity",
          [global_connectivity](const Graph& g, bool directed) {
              return global_connectivity(g, true, directed);
          },
          "graph"_a, "directed"_a = false,
          "Global node (vertex) connectivity: the minimum number of nodes whose "
          "removal disconnects the graph. Returns 0 for a graph with fewer than "
          "two nodes.");
    m.def("node_connectivity",
          [local_connectivity](const Graph& g, node s, node t, bool directed) {
              return local_connectivity(g, s, t, true, directed);
          },
          "graph"_a, "source"_a, "target"_a, "directed"_a = false,
          "Local node connectivity: the maximum number of internally "
          "node-disjoint source-to-target paths (Menger).");
    m.def("edge_connectivity",
          [global_connectivity](const Graph& g, bool directed) {
              return global_connectivity(g, false, directed);
          },
          "graph"_a, "directed"_a = false,
          "Global edge connectivity: the minimum number of edges whose removal "
          "disconnects the graph. Returns 0 for a graph with fewer than two "
          "nodes.");
    m.def("edge_connectivity",
          [local_connectivity](const Graph& g, node s, node t, bool directed) {
              return local_connectivity(g, s, t, false, directed);
          },
          "graph"_a, "source"_a, "target"_a, "directed"_a = false,
          "Local edge connectivity: the maximum number of edge-disjoint "
          "source-to-target paths (Menger).");

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
              ogdfpy::require_same_graph(num, g, "topological_numbering",
                                         "numbering");
              ogdfpy::require_acyclic(g, "topological_numbering");
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
    m.def("triangulate",
          [](Graph& g) {
              ogdfpy::require_min_nodes(g, 3, "triangulate");
              ogdfpy::require_simple(g, "triangulate");
              ogdfpy::require_connected(g, "triangulate");
              ogdfpy::require_planar_embedded(g, "triangulate");
              triangulate(g);
          },
          "graph"_a,
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
    m.def("represents_comb_embedding",
          [](const Graph& g) { return g.representsCombEmbedding(); },
          "graph"_a,
          "True if the current adjacency-list order is a valid combinatorial "
          "(planar) embedding, i.e. planar_embed has been applied.");

    // ---------------------------------------------------------------- //
    // Shortest paths                                                   //
    // ---------------------------------------------------------------- //
    m.def("dijkstra",
          [](const Graph& g, const EdgeArray<double>& weight, node source,
             NodeArray<double>& distance, bool directed) {
              ogdfpy::require_node(source, "dijkstra", "source");
              ogdfpy::require_same_graph(weight, g, "dijkstra", "weight");
              ogdfpy::require_same_graph(distance, g, "dijkstra", "distance");
              ogdfpy::require_non_negative(weight, g, "dijkstra", "weight");
              NodeArray<edge> predecessor(g);
              Dijkstra<double>().call(g, weight, source, predecessor, distance,
                                      directed);
          },
          "graph"_a, "weight"_a, "source"_a, "distance"_a,
          "directed"_a = false,
          "Single-source shortest paths; writes distances into `distance`.");
    m.def("bfs_distances",
          [](const Graph& g, node source, NodeArray<int>& distance) {
              ogdfpy::require_node(source, "bfs_distances", "source");
              ogdfpy::require_same_graph(distance, g, "bfs_distances",
                                         "distance");
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
              ogdfpy::require_same_graph(weight, g, "min_spanning_tree",
                                         "weight");
              ogdfpy::require_same_graph(in_tree, g, "min_spanning_tree",
                                         "in_tree");
              return computeMinST(g, weight, in_tree);
          },
          "graph"_a, "weight"_a, "in_tree"_a,
          "Minimum spanning tree (Prim). Returns total weight; marks tree "
          "edges in `in_tree`. Does not modify the graph.");
    m.def("make_minimum_spanning_tree",
          [](Graph& g, const EdgeArray<double>& weight) {
              ogdfpy::require_same_graph(weight, g,
                                         "make_minimum_spanning_tree", "weight");
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
              ogdfpy::require_node(s, "max_flow", "source");
              ogdfpy::require_node(t, "max_flow", "sink");
              ogdfpy::require_distinct(s, t, "max_flow");
              ogdfpy::require_same_graph(capacity, g, "max_flow", "capacity");
              ogdfpy::require_same_graph(flow, g, "max_flow", "flow");
              ogdfpy::require_non_negative(capacity, g, "max_flow", "capacity");
              EdgeArray<double> cap(capacity);  // computeFlow needs non-const
              MaxFlowGoldbergTarjan<double> mf(g);
              return mf.computeFlow(cap, s, t, flow);
          },
          "graph"_a, "capacity"_a, "source"_a, "sink"_a, "flow"_a,
          "Maximum s-t flow (Goldberg-Tarjan). Returns the flow value; writes "
          "per-edge flow into `flow`.");
    m.def("min_cut",
          [](const Graph& g, const EdgeArray<double>& weight) {
              ogdfpy::require_min_nodes(g, 2, "min_cut");
              ogdfpy::require_same_graph(weight, g, "min_cut", "weight");
              ogdfpy::require_non_negative(weight, g, "min_cut", "weight");
              MinimumCutStoerWagner<double> mc;
              return mc.call(g, weight);
          },
          "graph"_a, "weight"_a,
          "Global minimum cut value (Stoer-Wagner) for an undirected weighted "
          "graph.");
    m.def("min_st_cut",
          [](const Graph& g, const EdgeArray<double>& weight, node s, node t,
             bool directed) {
              ogdfpy::require_node(s, "min_st_cut", "source");
              ogdfpy::require_node(t, "min_st_cut", "sink");
              ogdfpy::require_distinct(s, t, "min_st_cut");
              ogdfpy::require_same_graph(weight, g, "min_st_cut", "weight");
              ogdfpy::require_non_negative(weight, g, "min_st_cut", "weight");
              // Cut edges are those leaving the source side; treatAsUndirected
              // is the inverse of `directed`. With directed=True the cut value
              // equals the directed max flow (max-flow min-cut duality).
              List<edge> cut;
              MinSTCutMaxFlow<double> mc(/*treatAsUndirected=*/!directed);
              mc.call(g, weight, s, t, cut);
              double value = 0.0;
              nb::list edges;
              for (edge e : cut) {
                  value += weight[e];
                  edges.append(nb::cast(e, nb::rv_policy::reference));
              }
              return nb::make_tuple(value, edges);
          },
          "graph"_a, "weight"_a, "source"_a, "sink"_a, "directed"_a = true,
          "Minimum s-t cut. Returns (cut_value, [cut_edges]) where the edges "
          "are those crossing from the source side to the sink side. With "
          "`directed` (the default) the value equals the directed maximum flow "
          "from source to sink; set it False to treat edges as undirected.");

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
              ogdfpy::require_same_graph(matching, g,
                                         "maximum_matching_bipartite",
                                         "matching");
              if (!isBipartite(g, color)) {
                  ogdfpy::unmet("maximum_matching_bipartite",
                                "a bipartite graph");
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
              ogdfpy::require_same_graph(colors, g, "node_coloring", "colors");
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
    // A* search (point-to-point shortest path)                         //
    // ---------------------------------------------------------------- //
    m.def("a_star_search",
          [](const Graph& g, const EdgeArray<double>& cost, node source,
             node target, bool directed,
             nb::object heuristic) -> nb::object {
              ogdfpy::require_node(source, "a_star_search", "source");
              ogdfpy::require_node(target, "a_star_search", "target");
              ogdfpy::require_same_graph(cost, g, "a_star_search", "cost");
              ogdfpy::require_non_negative(cost, g, "a_star_search", "cost");
              // The heuristic is an optional Python callable node -> float; a
              // zero heuristic makes A* equivalent to Dijkstra.
              std::function<double(node)> h = [](node) { return 0.0; };
              if (!heuristic.is_none()) {
                  h = [heuristic](node v) {
                      return nb::cast<double>(
                          heuristic(nb::cast(v, nb::rv_policy::reference)));
                  };
              }
              NodeArray<edge> predecessor(g);
              double length = AStarSearch<double>(directed).call(
                  g, cost, source, target, predecessor, h);
              // predecessor[target] is null when no path exists (unless the
              // target is the source itself, a zero-length path).
              if (source != target && predecessor[target] == nullptr) {
                  return nb::none();
              }
              List<edge> reversed;
              for (node v = target; v != source;) {
                  edge e = predecessor[v];
                  reversed.pushFront(e);
                  v = e->opposite(v);
              }
              nb::list path;
              for (edge e : reversed) {
                  path.append(nb::cast(e, nb::rv_policy::reference));
              }
              return nb::make_tuple(length, path);
          },
          "graph"_a, "cost"_a, "source"_a, "target"_a, "directed"_a = false,
          "heuristic"_a = nb::none(),
          "A* shortest path from `source` to `target` with non-negative edge "
          "costs. `heuristic` is an optional callable mapping a node to an "
          "admissible lower-bound distance to the target (a zero heuristic "
          "reduces A* to Dijkstra). Returns (length, [path_edges]) or None if "
          "the target is unreachable.");

    // ---------------------------------------------------------------- //
    // General maximum-weight matching (Blossom V)                      //
    // ---------------------------------------------------------------- //
    m.def("maximum_weight_matching",
          [](const Graph& g, const EdgeArray<double>& weight,
             EdgeArray<bool>& matching) {
              ogdfpy::require_same_graph(weight, g,
                                         "maximum_weight_matching", "weight");
              ogdfpy::require_same_graph(matching, g,
                                         "maximum_weight_matching", "matching");
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
              ogdfpy::require_same_graph(weight, g, "steiner_tree", "weight");
              ogdfpy::require_non_negative(weight, g, "steiner_tree", "weight");
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
    // Crossing minimization                                            //
    // ---------------------------------------------------------------- //
    m.def("crossing_number",
          [](const Graph& g, int permutations) {
              if (permutations < 1) {
                  throw ogdfpy::PreconditionError(
                      "crossing_number: permutations must be >= 1");
              }
              // PlanRep copies the input graph, so `g` is not modified. The
              // planarizer works one connected component at a time; sum the
              // per-component crossing counts.
              PlanRep pr(g);
              SubgraphPlanarizer sp;
              sp.permutations(permutations);
              int total = 0;
              for (int cc = 0; cc < pr.numberOfCCs(); ++cc) {
                  int crossings = 0;
                  sp.call(pr, cc, crossings);
                  total += crossings;
              }
              return total;
          },
          "graph"_a, "permutations"_a = 1,
          "Heuristic minimum number of edge crossings (subgraph planarizer). "
          "Returns 0 for a planar graph. `permutations` sets the number of "
          "randomized restarts of the edge-insertion phase; more restarts can "
          "lower the count at higher cost. Does not modify the graph.");

    // ---------------------------------------------------------------- //
    // Edge insertion (routing with crossings)                          //
    // ---------------------------------------------------------------- //
    m.def("insert_edges",
          [](const Graph& g, nb::list edges) {
              // Deduplicate the requested edges, preserving the caller's order.
              List<edge> want;
              std::unordered_set<edge> seen;
              for (auto handle : edges) {
                  edge e = nb::cast<edge>(handle);
                  if (seen.insert(e).second) {
                      want.pushBack(e);
                  }
              }

              PlanRep pr(g);
              VariableEmbeddingInserter inserter;

              nb::list result;  // list of (edge, [crossed edges in order])
              for (int cc = 0; cc < pr.numberOfCCs(); ++cc) {
                  pr.initCC(cc);
                  PlanRepLight prl(pr);
                  prl.initCC(cc);

                  // Restrict the requested edges to this component.
                  List<edge> here;
                  for (edge e : want) {
                      if (prl.copy(e) != nullptr) {
                          here.pushBack(e);
                      }
                  }
                  if (here.empty()) {
                      continue;
                  }

                  // Remove them so `prl` holds the planar subgraph, then insert
                  // them back with crossings.
                  for (edge e : here) {
                      prl.delEdge(prl.copy(e));
                  }
                  if (!isPlanar(prl)) {
                      throw ogdfpy::InvalidGraphError(
                          "insert_edges requires the graph minus the given "
                          "edges to be planar");
                  }

                  Array<edge> to_insert(here.size());
                  int i = 0;
                  for (edge e : here) {
                      to_insert[i++] = e;
                  }
                  if (!Module::isSolution(inserter.callEx(prl, to_insert))) {
                      throw ogdfpy::AlgorithmError(
                          "insert_edges: the edge-insertion phase failed");
                  }

                  // Each inserted edge becomes a chain of copy edges; every
                  // node shared by two consecutive chain edges is a crossing
                  // dummy. The other original edge through that dummy is the
                  // edge being crossed.
                  for (edge e : here) {
                      nb::list route;
                      edge prev = nullptr;
                      for (edge ce : prl.chain(e)) {
                          if (prev != nullptr) {
                              node v = (ce->source() == prev->source() ||
                                        ce->source() == prev->target())
                                           ? ce->source()
                                           : ce->target();
                              for (adjEntry adj : v->adjEntries) {
                                  edge other = prl.original(adj->theEdge());
                                  if (other != nullptr && other != e) {
                                      route.append(nb::cast(
                                          other, nb::rv_policy::reference));
                                      break;
                                  }
                              }
                          }
                          prev = ce;
                      }
                      result.append(nb::make_tuple(
                          nb::cast(e, nb::rv_policy::reference), route));
                  }
              }
              return result;
          },
          "graph"_a, "edges"_a,
          "Route the given edges through the rest of the graph, which must be "
          "planar once those edges are removed. Returns a list of "
          "(edge, [crossed_edges]) pairs: for each requested edge, the original "
          "edges it crosses, in order from the edge's source to its target. An "
          "edge inserted without crossings maps to an empty list. Uses the "
          "variable-embedding inserter; does not modify the graph.");

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
              ogdfpy::require_min_nodes(g, 3, "spqr_tree_summary");
              ogdfpy::require_biconnected(g, "spqr_tree_summary");
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
