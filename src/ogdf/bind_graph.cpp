// Core graph model: Graph, Node, Edge, attribute arrays, GraphAttributes.

#include "bindings.h"

#include <nanobind/make_iterator.h>
#include <nanobind/stl/string.h>

#include <ogdf/basic/Graph.h>
#include <ogdf/basic/GraphAttributes.h>
#include <ogdf/basic/geometry.h>
#include <ogdf/basic/graphics.h>

using namespace ogdf;
using namespace nb::literals;

void register_graph(nb::module_& m) {
    // node / edge are raw pointers (NodeElement*/EdgeElement*) owned by the
    // Graph. Bind them as opaque handles; never let Python take ownership.
    nb::class_<NodeElement>(m, "Node")
        .def_prop_ro("index", &NodeElement::index)
        .def_prop_ro("degree", &NodeElement::degree)
        .def("__repr__", [](const NodeElement& n) {
            return "<ogdf.Node index=" + std::to_string(n.index()) + ">";
        });

    nb::class_<EdgeElement>(m, "Edge")
        .def_prop_ro("index", &EdgeElement::index)
        .def_prop_ro("source", &EdgeElement::source, nb::rv_policy::reference)
        .def_prop_ro("target", &EdgeElement::target, nb::rv_policy::reference)
        .def("__repr__", [](const EdgeElement& e) {
            return "<ogdf.Edge index=" + std::to_string(e.index()) + ">";
        });

    nb::class_<Graph>(m, "Graph")
        .def(nb::init<>())
        .def("new_node", [](Graph& g) { return g.newNode(); },
             nb::rv_policy::reference_internal, "Create and return a new node.")
        .def("new_edge",
             [](Graph& g, node s, node t) { return g.newEdge(s, t); },
             "source"_a, "target"_a, nb::rv_policy::reference_internal,
             "Create and return a new edge from source to target.")
        .def("number_of_nodes", &Graph::numberOfNodes)
        .def("number_of_edges", &Graph::numberOfEdges)
        .def("empty", &Graph::empty)
        .def("clear", &Graph::clear)
        .def("nodes",
             [](Graph& g) {
                 return nb::make_iterator<nb::rv_policy::reference>(
                     nb::type<Graph>(), "NodeIterator", g.nodes.begin(),
                     g.nodes.end());
             },
             nb::keep_alive<0, 1>(), "Iterate over the graph's nodes.")
        .def("edges",
             [](Graph& g) {
                 return nb::make_iterator<nb::rv_policy::reference>(
                     nb::type<Graph>(), "EdgeIterator", g.edges.begin(),
                     g.edges.end());
             },
             nb::keep_alive<0, 1>(), "Iterate over the graph's edges.")
        .def("__iter__",
             [](Graph& g) {
                 return nb::make_iterator<nb::rv_policy::reference>(
                     nb::type<Graph>(), "NodeIterator", g.nodes.begin(),
                     g.nodes.end());
             },
             nb::keep_alive<0, 1>())
        .def("__len__", &Graph::numberOfNodes)
        .def("__repr__", [](const Graph& g) {
            return "<ogdf.Graph nodes=" + std::to_string(g.numberOfNodes()) +
                   " edges=" + std::to_string(g.numberOfEdges()) + ">";
        });

    // Attribute arrays. Each is registered with its Graph and auto-resizes;
    // keep_alive<1,2> ties the array's lifetime to the Graph. These double as
    // the input/output containers for the algorithm bindings.
    auto bind_node_array = [&m](const char* name, auto sample) {
        using T = decltype(sample);
        nb::class_<NodeArray<T>>(m, name)
            .def(nb::init<const Graph&>(), "graph"_a, nb::keep_alive<1, 2>())
            .def(nb::init<const Graph&, T>(), "graph"_a, "default_value"_a,
                 nb::keep_alive<1, 2>())
            .def("__getitem__",
                 [](NodeArray<T>& a, node v) -> T { return a[v]; })
            .def("__setitem__",
                 [](NodeArray<T>& a, node v, T val) { a[v] = val; })
            .def("fill", [](NodeArray<T>& a, T val) { a.fill(val); }, "value"_a);
    };
    auto bind_edge_array = [&m](const char* name, auto sample) {
        using T = decltype(sample);
        nb::class_<EdgeArray<T>>(m, name)
            .def(nb::init<const Graph&>(), "graph"_a, nb::keep_alive<1, 2>())
            .def(nb::init<const Graph&, T>(), "graph"_a, "default_value"_a,
                 nb::keep_alive<1, 2>())
            .def("__getitem__",
                 [](EdgeArray<T>& a, edge e) -> T { return a[e]; })
            .def("__setitem__",
                 [](EdgeArray<T>& a, edge e, T val) { a[e] = val; })
            .def("fill", [](EdgeArray<T>& a, T val) { a.fill(val); }, "value"_a);
    };
    bind_node_array("NodeArrayInt", int{});
    bind_node_array("NodeArrayDouble", double{});
    bind_node_array("NodeArrayBool", bool{});
    bind_edge_array("EdgeArrayInt", int{});
    bind_edge_array("EdgeArrayDouble", double{});
    bind_edge_array("EdgeArrayBool", bool{});

    // --- styling: Color + enums, used by GraphAttributes accessors --- //
    nb::class_<Color>(m, "Color")
        .def(nb::init<int, int, int, int>(), "r"_a, "g"_a, "b"_a, "a"_a = 255)
        .def(nb::init<const std::string&>(), "value"_a,
             "Construct from a hex string like '#rrggbb'.")
        .def_prop_rw("red", [](const Color& c) { return c.red(); },
                     [](Color& c, uint8_t v) { c.red(v); })
        .def_prop_rw("green", [](const Color& c) { return c.green(); },
                     [](Color& c, uint8_t v) { c.green(v); })
        .def_prop_rw("blue", [](const Color& c) { return c.blue(); },
                     [](Color& c, uint8_t v) { c.blue(v); })
        .def_prop_rw("alpha", [](const Color& c) { return c.alpha(); },
                     [](Color& c, uint8_t v) { c.alpha(v); })
        .def("__repr__",
             [](const Color& c) { return "<ogdf.Color " + c.toString() + ">"; });

    nb::enum_<Shape>(m, "Shape")
        .value("RECT", Shape::Rect)
        .value("ROUNDED_RECT", Shape::RoundedRect)
        .value("ELLIPSE", Shape::Ellipse)
        .value("TRIANGLE", Shape::Triangle)
        .value("PENTAGON", Shape::Pentagon)
        .value("HEXAGON", Shape::Hexagon)
        .value("OCTAGON", Shape::Octagon)
        .value("RHOMB", Shape::Rhomb)
        .value("TRAPEZE", Shape::Trapeze)
        .value("PARALLELOGRAM", Shape::Parallelogram)
        .value("INV_TRIANGLE", Shape::InvTriangle)
        .value("INV_TRAPEZE", Shape::InvTrapeze)
        .value("INV_PARALLELOGRAM", Shape::InvParallelogram)
        .value("IMAGE", Shape::Image);

    nb::enum_<StrokeType>(m, "StrokeType")
        .value("NONE", StrokeType::None)
        .value("SOLID", StrokeType::Solid)
        .value("DASH", StrokeType::Dash)
        .value("DOT", StrokeType::Dot)
        .value("DASHDOT", StrokeType::Dashdot)
        .value("DASHDOTDOT", StrokeType::Dashdotdot);

    nb::enum_<FillPattern>(m, "FillPattern")
        .value("NONE", FillPattern::None)
        .value("SOLID", FillPattern::Solid)
        .value("DENSE1", FillPattern::Dense1)
        .value("DENSE2", FillPattern::Dense2)
        .value("DENSE3", FillPattern::Dense3)
        .value("DENSE4", FillPattern::Dense4)
        .value("DENSE5", FillPattern::Dense5)
        .value("DENSE6", FillPattern::Dense6)
        .value("DENSE7", FillPattern::Dense7)
        .value("HORIZONTAL", FillPattern::Horizontal)
        .value("VERTICAL", FillPattern::Vertical)
        .value("CROSS", FillPattern::Cross)
        .value("BACKWARD_DIAGONAL", FillPattern::BackwardDiagonal)
        .value("FORWARD_DIAGONAL", FillPattern::ForwardDiagonal)
        .value("DIAGONAL_CROSS", FillPattern::DiagonalCross);

    nb::enum_<EdgeArrow>(m, "EdgeArrow")
        .value("NONE", EdgeArrow::None)
        .value("LAST", EdgeArrow::Last)
        .value("FIRST", EdgeArrow::First)
        .value("BOTH", EdgeArrow::Both)
        .value("UNDEFINED", EdgeArrow::Undefined);

    // GraphAttributes: geometry, size, labels, and styling.
    nb::class_<GraphAttributes>(m, "GraphAttributes")
        .def(nb::init<const Graph&, long>(), "graph"_a,
             "attr"_a = (GraphAttributes::nodeGraphics |
                         GraphAttributes::edgeGraphics),
             nb::keep_alive<1, 2>())
        .def("x", [](GraphAttributes& g, node v) { return g.x(v); }, "node"_a)
        .def("y", [](GraphAttributes& g, node v) { return g.y(v); }, "node"_a)
        .def("set_x", [](GraphAttributes& g, node v, double v2) { g.x(v) = v2; },
             "node"_a, "value"_a)
        .def("set_y", [](GraphAttributes& g, node v, double v2) { g.y(v) = v2; },
             "node"_a, "value"_a)
        .def("width", [](GraphAttributes& g, node v) { return g.width(v); },
             "node"_a)
        .def("height", [](GraphAttributes& g, node v) { return g.height(v); },
             "node"_a)
        .def("set_width",
             [](GraphAttributes& g, node v, double w) { g.width(v) = w; },
             "node"_a, "value"_a)
        .def("set_height",
             [](GraphAttributes& g, node v, double h) { g.height(v) = h; },
             "node"_a, "value"_a)
        // Labels require the nodeLabel / edgeLabel flags to be enabled.
        .def("node_label",
             [](GraphAttributes& g, node v) { return g.label(v); }, "node"_a)
        .def("set_node_label",
             [](GraphAttributes& g, node v, const std::string& s) {
                 g.label(v) = s;
             },
             "node"_a, "label"_a)
        .def("edge_label",
             [](GraphAttributes& g, edge e) { return g.label(e); }, "edge"_a)
        .def("set_edge_label",
             [](GraphAttributes& g, edge e, const std::string& s) {
                 g.label(e) = s;
             },
             "edge"_a, "label"_a)
        // --- node styling (shape needs nodeGraphics; rest need nodeStyle) --- //
        .def("shape", [](GraphAttributes& g, node v) { return g.shape(v); },
             "node"_a)
        .def("set_shape",
             [](GraphAttributes& g, node v, Shape s) { g.shape(v) = s; },
             "node"_a, "shape"_a)
        .def("fill_color",
             [](GraphAttributes& g, node v) { return g.fillColor(v); },
             "node"_a)
        .def("set_fill_color",
             [](GraphAttributes& g, node v, const Color& c) {
                 g.fillColor(v) = c;
             },
             "node"_a, "color"_a)
        .def("set_fill_pattern",
             [](GraphAttributes& g, node v, FillPattern p) {
                 g.fillPattern(v) = p;
             },
             "node"_a, "pattern"_a)
        .def("node_stroke_color",
             [](GraphAttributes& g, node v) { return g.strokeColor(v); },
             "node"_a)
        .def("set_node_stroke_color",
             [](GraphAttributes& g, node v, const Color& c) {
                 g.strokeColor(v) = c;
             },
             "node"_a, "color"_a)
        .def("set_node_stroke_width",
             [](GraphAttributes& g, node v, float w) { g.strokeWidth(v) = w; },
             "node"_a, "width"_a)
        // --- edge styling (need edgeStyle / edgeArrow / edgeGraphics) --- //
        .def("edge_stroke_color",
             [](GraphAttributes& g, edge e) { return g.strokeColor(e); },
             "edge"_a)
        .def("set_edge_stroke_color",
             [](GraphAttributes& g, edge e, const Color& c) {
                 g.strokeColor(e) = c;
             },
             "edge"_a, "color"_a)
        .def("set_edge_stroke_width",
             [](GraphAttributes& g, edge e, float w) { g.strokeWidth(e) = w; },
             "edge"_a, "width"_a)
        .def("arrow", [](GraphAttributes& g, edge e) { return g.arrowType(e); },
             "edge"_a)
        .def("set_arrow",
             [](GraphAttributes& g, edge e, EdgeArrow a) {
                 g.arrowType(e) = a;
             },
             "edge"_a, "arrow"_a)
        .def("add_bend",
             [](GraphAttributes& g, edge e, double x, double y) {
                 g.bends(e).pushBack(DPoint(x, y));
             },
             "edge"_a, "x"_a, "y"_a,
             "Append a bend point to an edge's polyline.")
        .def("clear_bends",
             [](GraphAttributes& g, edge e) { g.bends(e).clear(); }, "edge"_a)
        .def("bounding_box_width",
             [](GraphAttributes& g) { return g.boundingBox().width(); })
        .def("bounding_box_height",
             [](GraphAttributes& g) { return g.boundingBox().height(); });

    // Attribute flag constants (combine with |).
    m.attr("NODE_GRAPHICS") = GraphAttributes::nodeGraphics;
    m.attr("EDGE_GRAPHICS") = GraphAttributes::edgeGraphics;
    m.attr("NODE_LABEL") = GraphAttributes::nodeLabel;
    m.attr("EDGE_LABEL") = GraphAttributes::edgeLabel;
    m.attr("NODE_STYLE") = GraphAttributes::nodeStyle;
    m.attr("EDGE_STYLE") = GraphAttributes::edgeStyle;
    m.attr("EDGE_ARROW") = GraphAttributes::edgeArrow;
    m.attr("ALL_ATTRIBUTES") = GraphAttributes::all;
}
