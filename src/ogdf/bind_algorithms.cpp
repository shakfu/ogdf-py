// Core graph algorithms: connectivity, components, shortest paths, spanning
// trees, flow, cut, matching, coloring, planarity.
//
// Algorithms that produce per-node / per-edge results follow OGDF's idiom: the
// caller passes a NodeArray*/EdgeArray* output object, and the function returns
// the scalar result (a count, weight, or flow value).

#include "bindings.h"
#include "errors.h"

#include <nanobind/stl/string.h>

#include <algorithm>
#include <cstdint>
#include <functional>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <vector>
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
#include <ogdf/graphalg/steiner_tree/EdgeWeightedGraph.h>
#include <ogdf/graphalg/steiner_tree/EdgeWeightedGraphCopy.h>

using namespace ogdf;
using namespace nb::literals;

namespace {

// Convert one item of a Python list to a handle of `g`. nb::cast would map
// None to nullptr and raise std::bad_cast for other types.
template <typename Handle>
Handle handle_of(nb::handle item, const Graph& g, const char* op,
                 const char* arg, const char* kind) {
    Handle h = nullptr;
    if (item.is_none() || !nb::try_cast<Handle>(item, h)) {
        throw nb::type_error((std::string(op) + ": every item of '" + arg +
                              "' must be an ogdf." + kind)
                                 .c_str());
    }
    ogdfpy::require_element_of(g, h, op, arg, kind == std::string("Node")
                                                  ? "node"
                                                  : "edge");
    return h;
}

// Kruskal over all edges: a minimum spanning forest, one tree per component.
// OGDF's computeMinST runs Prim from the first node and so covers only that
// node's component.
double min_spanning_forest(const Graph& g, const EdgeArray<double>& weight,
                           EdgeArray<bool>& in_tree) {
    std::vector<edge> order;
    order.reserve(g.numberOfEdges());
    for (edge e : g.edges) {
        in_tree[e] = false;
        if (!e->isSelfLoop()) {
            order.push_back(e);
        }
    }
    std::stable_sort(order.begin(), order.end(), [&weight](edge a, edge b) {
        return weight[a] < weight[b];
    });
    NodeArray<node> parent(g);
    for (node v : g.nodes) {
        parent[v] = v;
    }
    auto find = [&parent](node v) {
        while (parent[v] != v) {
            parent[v] = parent[parent[v]];
            v = parent[v];
        }
        return v;
    };
    double total = 0.0;
    for (edge e : order) {
        node a = find(e->source());
        node b = find(e->target());
        if (a != b) {
            parent[a] = b;
            in_tree[e] = true;
            total += weight[e];
        }
    }
    return total;
}

// Bellman-Ford with 64-bit accumulation that never relaxes out of an
// unreachable node. OGDF's ShortestPathWithBFM adds lengths to its INT_MAX
// sentinel, which overflows and corrupts every distance downstream of an
// unreachable node. Returns false if a negative cycle is reachable from s.
bool bellman_ford_checked(const Graph& g, node s, const EdgeArray<int>& length,
                          NodeArray<int>& distance,
                          NodeArray<edge>& predecessor, const char* op) {
    // |distance| <= sum |length|, so this bound keeps every distance in int
    // range and leaves INT_MAX free as the unreachable sentinel.
    std::int64_t bound = 0;
    for (edge e : g.edges) {
        bound += std::abs(static_cast<std::int64_t>(length[e]));
    }
    ogdfpy::require_arg(bound < std::numeric_limits<int>::max(), op,
                        "the sum of |length| must be below 2**31 - 1");
    constexpr std::int64_t kInf = std::numeric_limits<std::int64_t>::max();
    NodeArray<std::int64_t> d(g, kInf);
    for (node v : g.nodes) {
        predecessor[v] = nullptr;
    }
    d[s] = 0;
    auto relax = [&](bool update) {
        bool changed = false;
        for (edge e : g.edges) {
            node u = e->source();
            if (d[u] == kInf) {
                continue;
            }
            std::int64_t cand = d[u] + length[e];
            node v = e->target();
            if (cand < d[v]) {
                changed = true;
                if (!update) {
                    return true;
                }
                d[v] = cand;
                predecessor[v] = e;
            }
        }
        return changed;
    };
    for (int i = 1; i < g.numberOfNodes(); ++i) {
        if (!relax(true)) {
            break;
        }
    }
    const bool ok = !relax(false);
    for (node v : g.nodes) {
        distance[v] = d[v] == kInf ? std::numeric_limits<int>::max()
                                   : static_cast<int>(d[v]);
    }
    return ok;
}

}  // namespace

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
              ogdfpy::require_same_graph(coloring, g, "is_bipartite",
                                         "coloring");
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
        ogdfpy::require_node_of(g, s, "connectivity", "source");
        ogdfpy::require_node_of(g, t, "connectivity", "target");
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
              ogdfpy::require_same_graph(component, g, "connected_components",
                                         "component");
              return connectedComponents(g, component);
          },
          "graph"_a, "component"_a,
          "Number of connected components; writes each node's id into "
          "`component`.");
    m.def("strong_components",
          [](const Graph& g, NodeArray<int>& component) {
              ogdfpy::require_same_graph(component, g, "strong_components",
                                         "component");
              return strongComponents(g, component);
          },
          "graph"_a, "component"_a,
          "Number of strongly connected components (node ids into "
          "`component`).");
    m.def("biconnected_components",
          [](const Graph& g, EdgeArray<int>& component) {
              ogdfpy::require_same_graph(component, g, "biconnected_components",
                                         "component");
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
    // On non-planar input OGDF modifies the graph (K5 gains two nodes) and
    // marks the result as embedded.
    m.def("planar_embed_planar_graph",
          [](Graph& g) {
              ogdfpy::require_planar(g, "planar_embed_planar_graph");
              return planarEmbedPlanarGraph(g);
          },
          "graph"_a,
          "Faster planar embedding for a planar graph. Raises "
          "InvalidGraphError if the graph is not planar.");
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
              ogdfpy::require_node_of(g, source, "dijkstra", "source");
              ogdfpy::require_same_graph(weight, g, "dijkstra", "weight");
              ogdfpy::require_same_graph(distance, g, "dijkstra", "distance");
              ogdfpy::require_non_negative(weight, g, "dijkstra", "weight");
              NodeArray<edge> predecessor(g);
              Dijkstra<double>().call(g, weight, source, predecessor, distance,
                                      directed);
          },
          "graph"_a, "weight"_a, "source"_a, "distance"_a,
          "directed"_a = false,
          "Single-source shortest paths (Dijkstra; exact, requires non-negative "
          "weights). Writes distances into `distance`; an unreachable node gets "
          "the sentinel sys.float_info.max, not infinity. With `directed` False "
          "every edge is usable in both directions. Parallel edges are honoured "
          "individually, so the cheapest one wins. Use `shortest_paths()` for "
          "the paths themselves.");

    // Low-level primitive behind `shortest_paths()`: the same computation, but
    // also reporting the shortest-path tree that Dijkstra builds internally and
    // that the array-output form above discards.
    m.def("dijkstra_tree",
          [](const Graph& g, const EdgeArray<double>& weight, node source,
             bool directed) {
              ogdfpy::require_node_of(g, source, "dijkstra_tree", "source");
              ogdfpy::require_same_graph(weight, g, "dijkstra_tree", "weight");
              ogdfpy::require_non_negative(weight, g, "dijkstra_tree", "weight");
              NodeArray<edge> predecessor(g);
              NodeArray<double> distance(g);
              Dijkstra<double>().call(g, weight, source, predecessor, distance,
                                      directed);
              // Parallel lists in node iteration order; the Python layer keys
              // them by node index.
              nb::list distances;
              nb::list predecessors;
              for (node v : g.nodes) {
                  distances.append(distance[v]);
                  predecessors.append(
                      predecessor[v] == nullptr
                          ? nb::none()
                          : ogdfpy::to_python(predecessor[v], g));
              }
              return nb::make_tuple(distances, predecessors);
          },
          "graph"_a, "weight"_a, "source"_a, "directed"_a = false,
          "Dijkstra returning (distances, predecessor_edges) as lists in node "
          "iteration order. The predecessor of the source, and of every "
          "unreachable node, is None. Prefer `shortest_paths()`, which wraps "
          "this in a result object.");
    m.def("bfs_distances",
          [](const Graph& g, node source, NodeArray<int>& distance) {
              ogdfpy::require_node_of(g, source, "bfs_distances", "source");
              ogdfpy::require_same_graph(distance, g, "bfs_distances",
                                         "distance");
              bfs_SPSS<int>(source, g, distance, 1);
          },
          "graph"_a, "source"_a, "distance"_a,
          "Unweighted single-source distances (BFS; exact) in edge hops, "
          "written into `distance`. Edges are treated as undirected. "
          "Unreachable nodes keep the array's initial value, so initialise it "
          "with a sentinel you can recognise; `shortest_paths()` reports "
          "unreachability explicitly instead.");

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
              ogdfpy::require_no_nan(weight, g, "min_spanning_tree", "weight");
              return min_spanning_forest(g, weight, in_tree);
          },
          "graph"_a, "weight"_a, "in_tree"_a,
          "Minimum spanning tree (Kruskal; exact). Returns total weight; marks "
          "tree edges in `in_tree`, which `edges_where()` turns into a list. "
          "Edge direction is ignored. On a disconnected graph this yields a "
          "minimum spanning *forest*. Does not modify the graph.");
    m.def("make_minimum_spanning_tree",
          [](Graph& g, const EdgeArray<double>& weight) {
              ogdfpy::require_same_graph(weight, g,
                                         "make_minimum_spanning_tree", "weight");
              ogdfpy::require_no_nan(weight, g, "make_minimum_spanning_tree",
                                     "weight");
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
              ogdfpy::require_node_of(g, s, "max_flow", "source");
              ogdfpy::require_node_of(g, t, "max_flow", "sink");
              ogdfpy::require_distinct(s, t, "max_flow");
              ogdfpy::require_same_graph(capacity, g, "max_flow", "capacity");
              ogdfpy::require_same_graph(flow, g, "max_flow", "flow");
              ogdfpy::require_non_negative(capacity, g, "max_flow", "capacity");
              EdgeArray<double> cap(capacity);  // computeFlow needs non-const
              MaxFlowGoldbergTarjan<double> mf(g);
              return mf.computeFlow(cap, s, t, flow);
          },
          "graph"_a, "capacity"_a, "source"_a, "sink"_a, "flow"_a,
          "Maximum s-t flow (Goldberg-Tarjan; exact, requires non-negative "
          "capacities). Returns the flow value and writes the per-edge flow "
          "into `flow`. Edge direction is honoured and parallel edges carry "
          "flow independently. OGDF's max-flow module reports no cut; "
          "`min_st_cut()` gives the corresponding cut edges, and by max-flow "
          "min-cut duality its `value` equals the value returned here.");
    m.def("min_cut",
          [](const Graph& g, const EdgeArray<double>& weight) {
              ogdfpy::require_min_nodes(g, 2, "min_cut");
              ogdfpy::require_same_graph(weight, g, "min_cut", "weight");
              ogdfpy::require_non_negative(weight, g, "min_cut", "weight");
              MinimumCutStoerWagner<double> mc;
              return mc.call(g, weight);
          },
          "graph"_a, "weight"_a,
          "Global minimum cut value (Stoer-Wagner; exact) for an undirected "
          "weighted graph with non-negative weights. Returns the value only - "
          "use `min_st_cut()` when you need the cut edges or the partition.");
    m.def("st_cut",
          [](const Graph& g, const EdgeArray<double>& weight, node s, node t,
             bool directed) {
              ogdfpy::require_node_of(g, s, "st_cut", "source");
              ogdfpy::require_node_of(g, t, "st_cut", "sink");
              ogdfpy::require_distinct(s, t, "st_cut");
              ogdfpy::require_same_graph(weight, g, "st_cut", "weight");
              ogdfpy::require_non_negative(weight, g, "st_cut", "weight");
              // Cut edges are those leaving the source side; treatAsUndirected
              // is the inverse of `directed`. With directed=True the cut value
              // equals the directed max flow (max-flow min-cut duality).
              //
              // MinSTCutMaxFlow also exposes isInFrontCut()/isInBackCut(), but
              // those are NOT the two sides of the cut returned here: when the
              // minimum cut is not unique they describe the extreme cuts
              // nearest s and nearest t, which are different cuts, and neither
              // is guaranteed to correspond to this edge list. On the complete
              // digraph K20 the front cut is {s} while the returned edges are
              // the sink's in-edges. So the partition is deliberately not
              // reported - see the note in the docs.
              List<edge> cut;
              MinSTCutMaxFlow<double> mc(/*treatAsUndirected=*/!directed);
              mc.call(g, weight, s, t, cut);
              double value = 0.0;
              nb::list edges;
              for (edge e : cut) {
                  value += weight[e];
                  edges.append(ogdfpy::to_python(e, g));
              }
              return nb::make_tuple(value, edges);
          },
          "graph"_a, "weight"_a, "source"_a, "sink"_a, "directed"_a = true,
          "Minimum s-t cut (exact, requires non-negative weights) returning "
          "(value, cut_edges). A minimum cut need not be unique; which one is "
          "reported is OGDF's choice. Prefer `min_st_cut()`, which wraps this "
          "in a result object with named fields.");

    // ---------------------------------------------------------------- //
    // Matching                                                         //
    // ---------------------------------------------------------------- //
    m.def("maximal_matching",
          [](const Graph& g) {
              ArrayBuffer<edge> matching;
              Matching::findMaximalMatching(g, matching);
              nb::list out;
              for (edge e : matching) {
                  out.append(ogdfpy::to_python(e, g));
              }
              return out;
          },
          "graph"_a,
          "A maximal matching as a list of edges (greedy; maximal, meaning no "
          "edge can be added - not maximum cardinality. Use "
          "`maximum_weight_matching` or `maximum_matching_bipartite` for an "
          "optimal one).");
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
          "Proper node colouring (Recursive Largest First; heuristic - the "
          "colour count is an upper bound, not the chromatic number). Returns "
          "the number of colours used; writes each node's colour into "
          "`colors`.");

    // ---------------------------------------------------------------- //
    // Cut vertices and bridges                                         //
    // ---------------------------------------------------------------- //
    m.def("cut_vertices",
          [](const Graph& g) {
              ArrayBuffer<node> cut;
              findCutVertices(g, cut);
              nb::list out;
              for (node v : cut) {
                  out.append(ogdfpy::to_python(v, g));
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
                      out.append(ogdfpy::to_python(e, g));
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
              ogdfpy::require_node_of(g, source, "bellman_ford", "source");
              ogdfpy::require_same_graph(length, g, "bellman_ford", "length");
              ogdfpy::require_same_graph(distance, g, "bellman_ford",
                                         "distance");
              NodeArray<edge> predecessor(g);
              return bellman_ford_checked(g, source, length, distance,
                                          predecessor, "bellman_ford");
          },
          "graph"_a, "source"_a, "length"_a, "distance"_a,
          "Bellman-Ford single-source shortest paths (exact) on a directed "
          "graph with integer (possibly negative) edge lengths. Returns False "
          "if a negative cycle is reachable from the source; writes distances "
          "into `distance`, with 2**31 - 1 for unreachable nodes. The sum of "
          "|length| must be below 2**31 - 1. Edge "
          "direction is always honoured - unlike `dijkstra`, there is no "
          "undirected mode. Lengths are integers because OGDF's shortest-path "
          "module interface is defined over int; `dijkstra` and "
          "`a_star_search` take doubles, but neither admits negative weights. "
          "Use `shortest_paths(algorithm=\'bellman_ford\')` for the paths.");

    // Low-level primitive behind `shortest_paths(algorithm="bellman_ford")`.
    m.def("bellman_ford_tree",
          [](const Graph& g, node source, const EdgeArray<int>& length) {
              ogdfpy::require_node_of(g, source, "bellman_ford_tree", "source");
              ogdfpy::require_same_graph(length, g, "bellman_ford_tree",
                                         "length");
              NodeArray<edge> predecessor(g);
              NodeArray<int> distance(g);
              const bool ok =
                  bellman_ford_checked(g, source, length, distance,
                                       predecessor, "bellman_ford_tree");
              nb::list distances;
              nb::list predecessors;
              for (node v : g.nodes) {
                  distances.append(distance[v]);
                  predecessors.append(
                      predecessor[v] == nullptr
                          ? nb::none()
                          : ogdfpy::to_python(predecessor[v], g));
              }
              return nb::make_tuple(ok, distances, predecessors);
          },
          "graph"_a, "source"_a, "length"_a,
          "Bellman-Ford returning (ok, distances, predecessor_edges), the "
          "lists in node iteration order. `ok` is False if a negative cycle "
          "exists, in which case the other two are meaningless. Prefer "
          "`shortest_paths()`.");

    // ---------------------------------------------------------------- //
    // A* search (point-to-point shortest path)                         //
    // ---------------------------------------------------------------- //
    m.def("a_star_search",
          [](const Graph& g, const EdgeArray<double>& cost, node source,
             node target, bool directed,
             nb::object heuristic) -> nb::object {
              ogdfpy::require_node_of(g, source, "a_star_search", "source");
              ogdfpy::require_node_of(g, target, "a_star_search", "target");
              ogdfpy::require_same_graph(cost, g, "a_star_search", "cost");
              ogdfpy::require_non_negative(cost, g, "a_star_search", "cost");
              // The heuristic is an optional Python callable node -> float; a
              // zero heuristic makes A* equivalent to Dijkstra.
              std::function<double(node)> h = [](node) { return 0.0; };
              if (!heuristic.is_none()) {
                  h = [heuristic, &g](node v) {
                      return nb::cast<double>(
                          heuristic(ogdfpy::to_python(v, g)));
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
                  path.append(ogdfpy::to_python(e, g));
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
              ogdfpy::require_no_nan(weight, g, "maximum_weight_matching",
                                     "weight");
              for (edge e : g.edges) {
                  if (e->isSelfLoop()) {
                      ogdfpy::unmet("maximum_weight_matching",
                                    "a graph without self-loops");
                  }
              }
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
          "Maximum-weight general matching (Blossom V; exact). Returns the "
          "total weight and marks matched edges in `matching`, which "
          "`edges_where()` turns into a list. Edge direction is ignored.");

    // ---------------------------------------------------------------- //
    // Minimum-cost flow                                                //
    // ---------------------------------------------------------------- //
    m.def("min_cost_flow",
          [](const Graph& g, const EdgeArray<int>& lower_bound,
             const EdgeArray<int>& upper_bound, const EdgeArray<double>& cost,
             const NodeArray<int>& supply, EdgeArray<int>& flow) {
              const char* op = "min_cost_flow";
              ogdfpy::require_same_graph(lower_bound, g, op, "lower_bound");
              ogdfpy::require_same_graph(upper_bound, g, op, "upper_bound");
              ogdfpy::require_same_graph(cost, g, op, "cost");
              ogdfpy::require_same_graph(supply, g, op, "supply");
              ogdfpy::require_same_graph(flow, g, op, "flow");
              ogdfpy::require_connected(g, op);
              for (edge e : g.edges) {
                  ogdfpy::require_arg(
                      lower_bound[e] <= upper_bound[e], op,
                      "lower_bound exceeds upper_bound on edge " +
                          std::to_string(e->index()));
                  ogdfpy::require_arg(std::isfinite(cost[e]), op,
                                      "cost is not finite on edge " +
                                          std::to_string(e->index()));
              }
              std::int64_t total = 0;
              for (node v : g.nodes) {
                  total += supply[v];
              }
              ogdfpy::require_arg(total == 0, op, "supplies must sum to zero");
              const bool ok = MinCostFlowReinelt<double>().call(
                  g, lower_bound, upper_bound, cost, supply, flow);
              // Reinelt reports success with a zero flow on a one-edge
              // network, so verify every solution it calls feasible.
              double value = 0.0;
              if (ok && !MinCostFlowModule<double>::checkComputedFlow(
                            g, lower_bound, upper_bound, cost, supply, flow,
                            value)) {
                  throw ogdfpy::AlgorithmError(
                      "min_cost_flow: OGDF returned a flow that violates the "
                      "bounds or flow conservation");
              }
              return ok;
          },
          "graph"_a, "lower_bound"_a, "upper_bound"_a, "cost"_a, "supply"_a,
          "flow"_a,
          "Minimum-cost flow (Reinelt) on a connected graph. Bounds, supply, "
          "and flow are integers, with lower_bound <= upper_bound; cost is a "
          "finite float. Node supply is positive for sources and negative for "
          "sinks and must sum to zero. Returns False if infeasible; writes "
          "per-edge flow into `flow`. Raises AlgorithmError if OGDF reports a "
          "flow that fails verification.");

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
              NodeArray<int> component(g);
              connectedComponents(g, component);
              int terminal_component = -1;
              for (auto handle : terminals) {
                  node v = handle_of<node>(handle, g, "steiner_tree",
                                           "terminals", "Node");
                  if (terminal_component == -1) {
                      terminal_component = component[v];
                  } else if (component[v] != terminal_component) {
                      throw ogdfpy::InvalidGraphError(
                          "steiner_tree requires all terminals to lie in one "
                          "connected component");
                  }
                  node v2 = to_ewg[v];
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
                          edges.append(
                              ogdfpy::to_python(to_user_edge[ewg_edge], g));
                      }
                  }
                  delete tree;
              }
              return nb::make_tuple(total, edges);
          },
          "graph"_a, "weight"_a, "terminals"_a,
          "Minimum Steiner tree connecting the given terminals (Mehlhorn; a "
          "2-approximation, not exact). Requires non-negative weights and "
          "ignores edge direction; duplicate terminals are collapsed. Returns "
          "(total_weight, [tree_edges]).");

    // ---------------------------------------------------------------- //
    // Maximal planar subgraph                                          //
    // ---------------------------------------------------------------- //
    m.def("maximal_planar_subgraph",
          [](const Graph& g) {
              List<edge> del_edges;
              MaximalPlanarSubgraphSimple<int>().call(g, del_edges);
              nb::list out;
              for (edge e : del_edges) {
                  out.append(ogdfpy::to_python(e, g));
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
                  edge e = handle_of<edge>(handle, g, "insert_edges", "edges",
                                           "Edge");
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
                                      route.append(ogdfpy::to_python(other, g));
                                      break;
                                  }
                              }
                          }
                          prev = ce;
                      }
                      result.append(nb::make_tuple(
                          ogdfpy::to_python(e, g), route));
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
              // On a non-biconnected graph OGDF reports a cut vertex in s1 and
              // leaves s2 null, which read as "triconnected".
              ogdfpy::require_biconnected(g, "separation_pair");
              node s1 = nullptr;
              node s2 = nullptr;
              isTriconnected(g, s1, s2);
              if (s1 != nullptr && s2 != nullptr) {
                  return nb::make_tuple(
                      ogdfpy::to_python(s1, g),
                      ogdfpy::to_python(s2, g));
              }
              return nb::none();
          },
          "graph"_a,
          "Return one separation pair (2-cut) as (node, node) for a "
          "biconnected but not triconnected graph, or None if the graph is "
          "triconnected. Raises InvalidGraphError if the graph is not "
          "biconnected; use cut_vertices() for those.");
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
