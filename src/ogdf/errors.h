// The exception taxonomy raised by the bindings, plus the precondition checks
// shared across translation units.
//
// OGDF documents preconditions but, with assertions compiled out of a release
// build, violating one is undefined behaviour rather than a diagnosable error.
// Every wrapper whose underlying algorithm has a documented precondition should
// therefore check it here first, so Python sees a typed, actionable exception
// instead of a crash or a silently wrong drawing.
//
// The C++ types below are mapped to Python classes in bind_errors.cpp. All of
// them derive from `ogdf.OGDFError`, and the ones that describe bad arguments
// also derive from Python's `ValueError` so existing `except ValueError` code
// keeps working.

#pragma once

#include "bindings.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

#include <ogdf/basic/Graph.h>
#include <ogdf/basic/GraphAttributes.h>
#include <ogdf/basic/extended_graph_alg.h>
#include <ogdf/basic/simple_graph_alg.h>

namespace ogdfpy {

// Base of every error the bindings raise deliberately.
struct OGDFError : std::runtime_error {
    using std::runtime_error::runtime_error;
};

// A documented precondition of the called operation is not satisfied.
struct PreconditionError : OGDFError {
    using OGDFError::OGDFError;
};

// The graph itself has the wrong structure for the operation (not planar, not
// a tree, not connected, ...). A more specific PreconditionError.
struct InvalidGraphError : PreconditionError {
    using PreconditionError::PreconditionError;
};

// A file format cannot represent what was asked of it, or is not recognized.
struct UnsupportedFormatError : OGDFError {
    using OGDFError::OGDFError;
};

// The algorithm ran but could not produce a result (no feasible solution, a
// numerical failure, an internal OGDF failure).
struct AlgorithmError : OGDFError {
    using OGDFError::OGDFError;
};

// --- precondition checks ------------------------------------------------- //
//
// Each takes the caller-facing name of the operation so the message says which
// call failed and what it needed, e.g.
//     TutteLayout requires a triconnected graph
//
// `what` describes the requirement in the same voice, for the rare check that
// does not have a dedicated helper.

[[noreturn]] inline void unmet(const char* op, const std::string& what) {
    throw InvalidGraphError(std::string(op) + " requires " + what);
}

inline void require_min_nodes(const ogdf::Graph& g, int n, const char* op) {
    if (g.numberOfNodes() < n) {
        unmet(op, "at least " + std::to_string(n) + " nodes");
    }
}

inline void require_non_empty(const ogdf::Graph& g, const char* op) {
    if (g.empty()) {
        unmet(op, "a non-empty graph");
    }
}

inline void require_simple(const ogdf::Graph& g, const char* op) {
    if (!ogdf::isSimpleUndirected(g)) {
        unmet(op, "a simple graph (no self-loops or parallel edges)");
    }
}

inline void require_connected(const ogdf::Graph& g, const char* op) {
    if (!ogdf::isConnected(g)) {
        unmet(op, "a connected graph");
    }
}

inline void require_biconnected(const ogdf::Graph& g, const char* op) {
    if (!ogdf::isBiconnected(g)) {
        unmet(op, "a biconnected graph");
    }
}

inline void require_triconnected(const ogdf::Graph& g, const char* op) {
    if (!ogdf::isTriconnected(g)) {
        unmet(op, "a triconnected graph");
    }
}

inline void require_planar(const ogdf::Graph& g, const char* op) {
    if (!ogdf::isPlanar(g)) {
        unmet(op, "a planar graph");
    }
}

inline void require_acyclic(const ogdf::Graph& g, const char* op) {
    if (!ogdf::isAcyclic(g)) {
        unmet(op, "a directed acyclic graph (it contains a directed cycle)");
    }
}

inline void require_forest(const ogdf::Graph& g, const char* op) {
    // TreeLayout draws each component of a rooted forest; the structural
    // requirement is that the underlying undirected graph has no cycle.
    if (!ogdf::isAcyclicUndirected(g)) {
        unmet(op, "a tree or forest (it contains an undirected cycle)");
    }
}

inline void require_tree(const ogdf::Graph& g, const char* op) {
    if (!ogdf::isTree(g)) {
        unmet(op, "a tree (a connected acyclic graph)");
    }
}

inline void require_planar_embedded(const ogdf::Graph& g, const char* op) {
    // An embedding is a property of the adjacency-list order, so the only
    // thing that can be checked cheaply is that one has been computed.
    if (!g.representsCombEmbedding()) {
        unmet(op,
              "a planar embedded graph; call planar_embed(graph) first");
    }
}

inline void require_distinct(ogdf::node s, ogdf::node t, const char* op) {
    if (s == t) {
        throw PreconditionError(std::string(op) +
                                " requires distinct source and target nodes");
    }
}

// Nodes and edges are raw handles owned by their Graph, and an array indexed by
// a handle from a different graph reads out of bounds. Check identity wherever
// a caller-supplied array meets a caller-supplied graph.
template <typename Array>
inline void require_same_graph(const Array& a, const ogdf::Graph& g,
                               const char* op, const char* arg) {
    const ogdf::Graph* owner = a.graphOf();
    if (owner != &g) {
        throw PreconditionError(
            std::string(op) + ": the '" + arg +
            "' array belongs to a different graph than the one passed in");
    }
}

// --- handle validity ------------------------------------------------------ //
//
// A Node or Edge is a raw pointer owned by its Graph. A release build of OGDF
// cannot map a handle to its graph, and a Python handle can outlive the element
// it names. Two mechanisms cover this, both driven by a GraphObserver attached
// to every Graph created from Python:
//
// - Liveness. When OGDF deletes an element, the Python instance wrapping it (if
//   any) is marked not ready, so nanobind refuses it as an argument with a
//   TypeError and a RuntimeWarning. Accessors therefore need no check. When a
//   new element reuses the address, the instance is marked ready again and then
//   names the new element; that is wrong-but-safe.
// - Membership. Each graph keeps its elements in arrays indexed by element
//   index, so `table[v->index()] == v` decides whether a live handle belongs to
//   that graph. Filling the arrays is sequential, so generators stay cheap.
//
// An earlier version kept a global address -> graph hash table. A lookup there
// cost a cache miss per access: 3x slower array access and generators.
// Everything here runs inside OGDF calls made with the GIL held.

class HandleTracker;

inline std::unordered_map<const ogdf::Graph*, HandleTracker*>& trackers() {
    static std::unordered_map<const ogdf::Graph*, HandleTracker*> map;
    return map;
}

// Created by Graph.__init__; deletes itself when the Graph is destroyed
// (~Graph calls clearObservers first, while its elements still exist).
class HandleTracker final : public ogdf::GraphObserver {
public:
    explicit HandleTracker(const ogdf::Graph& g) {
        trackers()[&g] = this;
        reregister(&g);
    }

    void nodeAdded(ogdf::node v) override {
        slot(nodes_, v->index()) = v;
        revive(v);
    }
    void nodeDeleted(ogdf::node v) override {
        nodes_[v->index()] = nullptr;
        invalidate(v);
    }
    void edgeAdded(ogdf::edge e) override {
        slot(edges_, e->index()) = e;
        revive(e);
    }
    void edgeDeleted(ogdf::edge e) override {
        edges_[e->index()] = nullptr;
        invalidate(e);
    }
    void cleared() override { forget(*getGraph()); }

    void registrationChanged(const ogdf::Graph* old) override {
        if (getGraph() == nullptr && old != nullptr) {
            forget(*old);
            trackers().erase(old);
            delete this;  // nothing touches *this after this callback returns
        }
    }

    // `v` must be live: dereferencing it reads its index.
    bool owns(ogdf::node v) const { return owns(nodes_, v); }
    bool owns(ogdf::edge e) const { return owns(edges_, e); }

private:
    template <typename Handle>
    static bool owns(const std::vector<Handle>& table, Handle h) {
        const auto i = static_cast<std::size_t>(h->index());
        return i < table.size() && table[i] == h;
    }

    template <typename Handle>
    static Handle& slot(std::vector<Handle>& table, int index) {
        const auto i = static_cast<std::size_t>(index);
        if (i >= table.size()) {
            table.resize(std::max(i + 1, 2 * table.size()), nullptr);
        }
        return table[i];
    }

    template <typename Element>
    static void invalidate(Element* h) {
        nb::object inst = nb::find(*h);
        if (inst.is_valid()) {
            nb::inst_set_state(inst, false, false);
        }
    }

    template <typename Element>
    static void revive(Element* h) {
        nb::object inst = nb::find(*h);
        if (inst.is_valid() && !nb::inst_ready(inst)) {
            nb::inst_set_state(inst, true, false);
        }
    }

    void forget(const ogdf::Graph& g) {
        for (ogdf::node v : g.nodes) {
            invalidate(v);
        }
        for (ogdf::edge e : g.edges) {
            invalidate(e);
        }
        nodes_.clear();
        edges_.clear();
    }

    std::vector<ogdf::node> nodes_;
    std::vector<ogdf::edge> edges_;
};

template <typename Handle>
inline void require_element_of(const ogdf::Graph& g, Handle h, const char* op,
                               const char* arg, const char* kind) {
    if (h == nullptr) {
        throw PreconditionError(std::string(op) + ": '" + arg +
                                "' must not be None");
    }
    auto it = trackers().find(&g);
    if (it == trackers().end() || !it->second->owns(h)) {
        throw PreconditionError(std::string(op) + ": '" + arg + "' is a " +
                                kind + " of a different graph");
    }
}

inline void require_node_of(const ogdf::Graph& g, ogdf::node v, const char* op,
                            const char* arg) {
    require_element_of(g, v, op, arg, "node");
}

inline void require_edge_of(const ogdf::Graph& g, ogdf::edge e, const char* op,
                            const char* arg) {
    require_element_of(g, e, op, arg, "edge");
}

// Cast a handle for return to Python, keeping its Graph alive. Used for the
// short lists algorithms return; iterators use rv_policy::reference, since a
// keep-alive record per handle costs memory and graph destruction invalidates
// the handles anyway.
template <typename Handle>
inline nb::object to_python(Handle h, const ogdf::Graph& g) {
    if (h == nullptr) {
        return nb::none();
    }
    nb::object parent = nb::find(g);
    if (!parent.is_valid()) {
        return nb::cast(h, nb::rv_policy::reference);
    }
    return nb::cast(h, nb::rv_policy::reference_internal, parent);
}

// Layouts, metrics, transforms and drawing writers read coordinates, sizes and
// bends, which exist only when these flags are enabled.
inline void require_graphics(const ogdf::GraphAttributes& ga, const char* op) {
    const long needed = ogdf::GraphAttributes::nodeGraphics |
                        ogdf::GraphAttributes::edgeGraphics;
    if (!ga.has(needed)) {
        throw PreconditionError(
            std::string(op) +
            " requires GraphAttributes with NODE_GRAPHICS and EDGE_GRAPHICS");
    }
}

inline void require_attribute(const ogdf::GraphAttributes& ga, long flag,
                              const char* flag_name, const char* op) {
    if (!ga.has(flag)) {
        throw PreconditionError(std::string(op) + " requires the " + flag_name +
                                " attribute; create the GraphAttributes with " +
                                flag_name + " (or ALL_ATTRIBUTES)");
    }
}

// Dijkstra, the Steiner-tree heuristic and the flow algorithms all assume
// non-negative values; a negative one yields a wrong answer rather than an
// error.
template <typename T>
inline void require_non_negative(const ogdf::EdgeArray<T>& a,
                                 const ogdf::Graph& g, const char* op,
                                 const char* arg) {
    for (ogdf::edge e : g.edges) {
        // Written as !(x >= 0) so NaN is rejected too.
        if (!(a[e] >= T(0))) {
            throw PreconditionError(std::string(op) + " requires non-negative '" +
                                    arg + "' values (edge " +
                                    std::to_string(e->index()) +
                                    " is negative or NaN)");
        }
    }
}

template <typename T>
inline void require_no_nan(const ogdf::EdgeArray<T>& a, const ogdf::Graph& g,
                           const char* op, const char* arg) {
    for (ogdf::edge e : g.edges) {
        if (std::isnan(static_cast<double>(a[e]))) {
            throw PreconditionError(std::string(op) + ": '" + arg +
                                    "' is NaN on edge " +
                                    std::to_string(e->index()));
        }
    }
}

// Generator and setter arguments.
inline void require_arg(bool ok, const char* op, const std::string& what) {
    if (!ok) {
        throw PreconditionError(std::string(op) + ": " + what);
    }
}

}  // namespace ogdfpy
