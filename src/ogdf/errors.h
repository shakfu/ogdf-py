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

#include <stdexcept>
#include <string>

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

// NodeElement::graphOf() exists only in an OGDF debug build, so a node handle
// from another graph cannot be detected here; the array check above is the
// enforceable half of that contract.
inline void require_node(ogdf::node v, const char* op, const char* arg) {
    if (v == nullptr) {
        throw PreconditionError(std::string(op) + ": '" + arg +
                                "' must not be None");
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
        if (a[e] < T(0)) {
            throw PreconditionError(std::string(op) + " requires non-negative '" +
                                    arg + "' values (edge " +
                                    std::to_string(e->index()) + " is negative)");
        }
    }
}

}  // namespace ogdfpy
