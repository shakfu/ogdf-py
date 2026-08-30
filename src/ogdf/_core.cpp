// nanobind bindings for a curated subset of the OGDF graph-drawing library.
//
// The bindings are split across translation units by concern (see bindings.h).
// This file is only the module entry point; it calls each register_* function.
// register_errors runs first so the exception types exist before anything can
// raise one; register_graph runs next because it registers the core types the
// other units reference.

#include "bindings.h"

NB_MODULE(_core, m) {
    m.doc() = "nanobind bindings for the OGDF graph-drawing library.";

    register_errors(m);
    register_graph(m);
    register_layouts(m);
    register_algorithms(m);
    register_io(m);
    register_generators(m);
    register_meta(m);
}
