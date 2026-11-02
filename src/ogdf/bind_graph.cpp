// Core graph model: Graph, Node, Edge, attribute arrays, GraphAttributes.

#include "bindings.h"
#include "errors.h"

#include <nanobind/make_iterator.h>
#include <nanobind/stl/string.h>

#include <ogdf/basic/Graph.h>
#include <ogdf/basic/GraphAttributes.h>
#include <ogdf/basic/geometry.h>
#include <ogdf/basic/graphics.h>

using namespace ogdf;
using namespace nb::literals;
using ogdfpy::require_attribute;
using ogdfpy::require_edge_of;
using ogdfpy::require_node_of;

void register_graph(nb::module_& m) {
    // node / edge are raw pointers (NodeElement*/EdgeElement*) owned by the
    // Graph. Bind them as opaque handles; never let Python take ownership.
    // A handle whose element was deleted is marked not ready, so nanobind
    // rejects it before any of these run (see ogdfpy::HandleTracker).
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
        .def("__init__",
             [](Graph* self) {
                 new (self) Graph();
                 new ogdfpy::HandleTracker(*self);  // owned by the Graph
             })
        .def("new_node", [](Graph& g) { return g.newNode(); },
             nb::rv_policy::reference_internal, "Create and return a new node.")
        .def("new_edge",
             [](Graph& g, node s, node t) {
                 require_node_of(g, s, "new_edge", "source");
                 require_node_of(g, t, "new_edge", "target");
                 return g.newEdge(s, t);
             },
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
                 [](NodeArray<T>& a, node v) -> T {
                     require_node_of(*a.graphOf(), v, "NodeArray", "node");
                     return a[v];
                 })
            .def("__setitem__",
                 [](NodeArray<T>& a, node v, T val) {
                     require_node_of(*a.graphOf(), v, "NodeArray", "node");
                     a[v] = val;
                 })
            .def("fill",
                 [](NodeArray<T>& a, T val) {
                     a.fill(val);
                 },
                 "value"_a);
    };
    auto bind_edge_array = [&m](const char* name, auto sample) {
        using T = decltype(sample);
        nb::class_<EdgeArray<T>>(m, name)
            .def(nb::init<const Graph&>(), "graph"_a, nb::keep_alive<1, 2>())
            .def(nb::init<const Graph&, T>(), "graph"_a, "default_value"_a,
                 nb::keep_alive<1, 2>())
            .def("__getitem__",
                 [](EdgeArray<T>& a, edge e) -> T {
                     require_edge_of(*a.graphOf(), e, "EdgeArray", "edge");
                     return a[e];
                 })
            .def("__setitem__",
                 [](EdgeArray<T>& a, edge e, T val) {
                     require_edge_of(*a.graphOf(), e, "EdgeArray", "edge");
                     a[e] = val;
                 })
            .def("fill",
                 [](EdgeArray<T>& a, T val) {
                     a.fill(val);
                 },
                 "value"_a);
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
             [](const Color& c) {
                 return "<ogdf.Color " + c.toString() + ">";
             });

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
        // The graph these attributes describe. Held by reference: the
        // GraphAttributes already keeps its Graph alive (keep_alive above), and
        // returning a copy would silently detach the two.
        .def_prop_ro("graph",
                     [](GraphAttributes& g) -> const Graph& {
                         return g.constGraph();
                     },
                     nb::rv_policy::reference_internal,
                     "The Graph these attributes describe.")
        .def("has", [](const GraphAttributes& g, long attr) {
                 return g.has(attr);
             },
             "attr"_a,
             "True if every flag in `attr` is enabled. Accessing an attribute "
             "whose flag is off is undefined, so check before reading data "
             "from an unknown source.")
        .def_prop_rw("directed",
                     [](const GraphAttributes& g) { return g.directed(); },
                     [](GraphAttributes& g, bool b) { g.directed() = b; },
                     "Whether the graph is written as directed by the file and "
                     "drawing writers.")
        .def("x",
             [](GraphAttributes& g, node v) {
                 require_attribute(g, GraphAttributes::nodeGraphics,
                                   "NODE_GRAPHICS", "GraphAttributes.x");
                 require_node_of(g.constGraph(), v, "GraphAttributes.x",
                                 "node");
                 return g.x(v);
             },
             "node"_a)
        .def("y",
             [](GraphAttributes& g, node v) {
                 require_attribute(g, GraphAttributes::nodeGraphics,
                                   "NODE_GRAPHICS", "GraphAttributes.y");
                 require_node_of(g.constGraph(), v, "GraphAttributes.y",
                                 "node");
                 return g.y(v);
             },
             "node"_a)
        .def("set_x",
             [](GraphAttributes& g, node v, double v2) {
                 require_attribute(g, GraphAttributes::nodeGraphics,
                                   "NODE_GRAPHICS", "GraphAttributes.set_x");
                 require_node_of(g.constGraph(), v, "GraphAttributes.set_x",
                                 "node");
                 g.x(v) = v2;
             },
             
             "node"_a, "value"_a)
        .def("set_y",
             [](GraphAttributes& g, node v, double v2) {
                 require_attribute(g, GraphAttributes::nodeGraphics,
                                   "NODE_GRAPHICS", "GraphAttributes.set_y");
                 require_node_of(g.constGraph(), v, "GraphAttributes.set_y",
                                 "node");
                 g.y(v) = v2;
             },
             
             "node"_a, "value"_a)
        .def("width",
             [](GraphAttributes& g, node v) {
                 require_attribute(g, GraphAttributes::nodeGraphics,
                                   "NODE_GRAPHICS", "GraphAttributes.width");
                 require_node_of(g.constGraph(), v, "GraphAttributes.width",
                                 "node");
                 return g.width(v);
             },
             
             "node"_a)
        .def("height",
             [](GraphAttributes& g, node v) {
                 require_attribute(g, GraphAttributes::nodeGraphics,
                                   "NODE_GRAPHICS", "GraphAttributes.height");
                 require_node_of(g.constGraph(), v, "GraphAttributes.height",
                                 "node");
                 return g.height(v);
             },
             
             "node"_a)
        .def("set_width",
             [](GraphAttributes& g, node v, double w) {
                 require_attribute(g, GraphAttributes::nodeGraphics,
                                   "NODE_GRAPHICS",
                                   "GraphAttributes.set_width");
                 require_node_of(g.constGraph(), v, "GraphAttributes.set_width",
                                 "node");
                 g.width(v) = w;
             },
             "node"_a, "value"_a)
        .def("set_height",
             [](GraphAttributes& g, node v, double h) {
                 require_attribute(g, GraphAttributes::nodeGraphics,
                                   "NODE_GRAPHICS",
                                   "GraphAttributes.set_height");
                 require_node_of(g.constGraph(), v,
                                 "GraphAttributes.set_height", "node");
                 g.height(v) = h;
             },
             "node"_a, "value"_a)
        // Labels require the nodeLabel / edgeLabel flags to be enabled.
        .def("node_label",
             [](GraphAttributes& g, node v) {
                 require_attribute(g, GraphAttributes::nodeLabel, "NODE_LABEL",
                                   "GraphAttributes.node_label");
                 require_node_of(g.constGraph(), v,
                                 "GraphAttributes.node_label", "node");
                 return g.label(v);
             }, "node"_a)
        .def("set_node_label",
             [](GraphAttributes& g, node v, const std::string& s) {
                 require_attribute(g, GraphAttributes::nodeLabel, "NODE_LABEL",
                                   "GraphAttributes.set_node_label");
                 require_node_of(g.constGraph(), v,
                                 "GraphAttributes.set_node_label", "node");
                 g.label(v) = s;
             },
             "node"_a, "label"_a)
        .def("edge_label",
             [](GraphAttributes& g, edge e) {
                 require_attribute(g, GraphAttributes::edgeLabel, "EDGE_LABEL",
                                   "GraphAttributes.edge_label");
                 require_edge_of(g.constGraph(), e,
                                 "GraphAttributes.edge_label", "edge");
                 return g.label(e);
             }, "edge"_a)
        .def("set_edge_label",
             [](GraphAttributes& g, edge e, const std::string& s) {
                 require_attribute(g, GraphAttributes::edgeLabel, "EDGE_LABEL",
                                   "GraphAttributes.set_edge_label");
                 require_edge_of(g.constGraph(), e,
                                 "GraphAttributes.set_edge_label", "edge");
                 g.label(e) = s;
             },
             "edge"_a, "label"_a)
        // --- node styling (shape needs nodeGraphics; rest need nodeStyle) --- //
        .def("shape",
             [](GraphAttributes& g, node v) {
                 require_attribute(g, GraphAttributes::nodeGraphics,
                                   "NODE_GRAPHICS", "GraphAttributes.shape");
                 require_node_of(g.constGraph(), v, "GraphAttributes.shape",
                                 "node");
                 return g.shape(v);
             },
             
             "node"_a)
        .def("set_shape",
             [](GraphAttributes& g, node v, Shape s) {
                 require_attribute(g, GraphAttributes::nodeGraphics,
                                   "NODE_GRAPHICS",
                                   "GraphAttributes.set_shape");
                 require_node_of(g.constGraph(), v, "GraphAttributes.set_shape",
                                 "node");
                 g.shape(v) = s;
             },
             "node"_a, "shape"_a)
        .def("fill_color",
             [](GraphAttributes& g, node v) {
                 require_attribute(g, GraphAttributes::nodeStyle, "NODE_STYLE",
                                   "GraphAttributes.fill_color");
                 require_node_of(g.constGraph(), v,
                                 "GraphAttributes.fill_color", "node");
                 return g.fillColor(v);
             },
             "node"_a)
        .def("set_fill_color",
             [](GraphAttributes& g, node v, const Color& c) {
                 require_attribute(g, GraphAttributes::nodeStyle, "NODE_STYLE",
                                   "GraphAttributes.set_fill_color");
                 require_node_of(g.constGraph(), v,
                                 "GraphAttributes.set_fill_color", "node");
                 g.fillColor(v) = c;
             },
             "node"_a, "color"_a)
        .def("set_fill_pattern",
             [](GraphAttributes& g, node v, FillPattern p) {
                 require_attribute(g, GraphAttributes::nodeStyle, "NODE_STYLE",
                                   "GraphAttributes.set_fill_pattern");
                 require_node_of(g.constGraph(), v,
                                 "GraphAttributes.set_fill_pattern", "node");
                 g.fillPattern(v) = p;
             },
             "node"_a, "pattern"_a)
        .def("node_stroke_color",
             [](GraphAttributes& g, node v) {
                 require_attribute(g, GraphAttributes::nodeStyle, "NODE_STYLE",
                                   "GraphAttributes.node_stroke_color");
                 require_node_of(g.constGraph(), v,
                                 "GraphAttributes.node_stroke_color", "node");
                 return g.strokeColor(v);
             },
             "node"_a)
        .def("set_node_stroke_color",
             [](GraphAttributes& g, node v, const Color& c) {
                 require_attribute(g, GraphAttributes::nodeStyle, "NODE_STYLE",
                                   "GraphAttributes.set_node_stroke_color");
                 require_node_of(g.constGraph(), v,
                                 "GraphAttributes.set_node_stroke_color",
                                 "node");
                 g.strokeColor(v) = c;
             },
             "node"_a, "color"_a)
        .def("set_node_stroke_width",
             [](GraphAttributes& g, node v, float w) {
                 require_attribute(g, GraphAttributes::nodeStyle, "NODE_STYLE",
                                   "GraphAttributes.set_node_stroke_width");
                 require_node_of(g.constGraph(), v,
                                 "GraphAttributes.set_node_stroke_width",
                                 "node");
                 g.strokeWidth(v) = w;
             },
             "node"_a, "width"_a)
        // --- edge styling (need edgeStyle / edgeArrow / edgeGraphics) --- //
        .def("edge_stroke_color",
             [](GraphAttributes& g, edge e) {
                 require_attribute(g, GraphAttributes::edgeStyle, "EDGE_STYLE",
                                   "GraphAttributes.edge_stroke_color");
                 require_edge_of(g.constGraph(), e,
                                 "GraphAttributes.edge_stroke_color", "edge");
                 return g.strokeColor(e);
             },
             "edge"_a)
        .def("set_edge_stroke_color",
             [](GraphAttributes& g, edge e, const Color& c) {
                 require_attribute(g, GraphAttributes::edgeStyle, "EDGE_STYLE",
                                   "GraphAttributes.set_edge_stroke_color");
                 require_edge_of(g.constGraph(), e,
                                 "GraphAttributes.set_edge_stroke_color",
                                 "edge");
                 g.strokeColor(e) = c;
             },
             "edge"_a, "color"_a)
        .def("set_edge_stroke_width",
             [](GraphAttributes& g, edge e, float w) {
                 require_attribute(g, GraphAttributes::edgeStyle, "EDGE_STYLE",
                                   "GraphAttributes.set_edge_stroke_width");
                 require_edge_of(g.constGraph(), e,
                                 "GraphAttributes.set_edge_stroke_width",
                                 "edge");
                 g.strokeWidth(e) = w;
             },
             "edge"_a, "width"_a)
        .def("arrow",
             [](GraphAttributes& g, edge e) {
                 require_attribute(g, GraphAttributes::edgeArrow, "EDGE_ARROW",
                                   "GraphAttributes.arrow");
                 require_edge_of(g.constGraph(), e, "GraphAttributes.arrow",
                                 "edge");
                 return g.arrowType(e);
             },
             
             "edge"_a)
        .def("set_arrow",
             [](GraphAttributes& g, edge e, EdgeArrow a) {
                 require_attribute(g, GraphAttributes::edgeArrow, "EDGE_ARROW",
                                   "GraphAttributes.set_arrow");
                 require_edge_of(g.constGraph(), e, "GraphAttributes.set_arrow",
                                 "edge");
                 g.arrowType(e) = a;
             },
             "edge"_a, "arrow"_a)
        .def("add_bend",
             [](GraphAttributes& g, edge e, double x, double y) {
                 require_attribute(g, GraphAttributes::edgeGraphics,
                                   "EDGE_GRAPHICS", "GraphAttributes.add_bend");
                 require_edge_of(g.constGraph(), e, "GraphAttributes.add_bend",
                                 "edge");
                 g.bends(e).pushBack(DPoint(x, y));
             },
             "edge"_a, "x"_a, "y"_a,
             "Append a bend point to an edge's polyline.")
        .def("clear_bends",
             [](GraphAttributes& g, edge e) {
                 require_attribute(g, GraphAttributes::edgeGraphics,
                                   "EDGE_GRAPHICS",
                                   "GraphAttributes.clear_bends");
                 require_edge_of(g.constGraph(), e,
                                 "GraphAttributes.clear_bends", "edge");
                 g.bends(e).clear();
             }, "edge"_a)
        .def("bounding_box_width",
             [](GraphAttributes& g) {
                 ogdfpy::require_graphics(g, "bounding_box_width");
                 return g.boundingBox().width();
             })
        .def("bounding_box_height",
             [](GraphAttributes& g) {
                 ogdfpy::require_graphics(g, "bounding_box_height");
                 return g.boundingBox().height();
             });

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
