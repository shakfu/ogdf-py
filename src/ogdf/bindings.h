// Shared declarations for the OGDF nanobind extension.
//
// The bindings are split across translation units by concern; NB_MODULE in
// _core.cpp calls each register_* function in order. register_graph must run
// first, since it registers the core types (Graph, Node, Edge, arrays,
// GraphAttributes) that the other units reference.

#pragma once

#include <nanobind/nanobind.h>

namespace nb = nanobind;

void register_graph(nb::module_& m);
void register_layouts(nb::module_& m);
void register_algorithms(nb::module_& m);
void register_io(nb::module_& m);
void register_generators(nb::module_& m);
