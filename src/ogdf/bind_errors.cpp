// Registers the Python exception classes the bindings raise (see errors.h).
//
// Registration order matters: nanobind checks translators most-recently-
// registered first, so a base class must be registered before its subclasses
// or the base would swallow the more specific type.
//
// The Python hierarchy deliberately mixes in the builtin exception that best
// matches each failure, so ordinary `except ValueError` / `except RuntimeError`
// code written against earlier versions keeps working:
//
//     Exception
//      +-- OGDFError
//           +-- PreconditionError      (also ValueError)
//           |    +-- InvalidGraphError
//           +-- UnsupportedFormatError (also ValueError)
//           +-- AlgorithmError         (also RuntimeError)

#include "errors.h"

using namespace ogdfpy;

void register_errors(nb::module_& m) {
    nb::object base =
        nb::exception<OGDFError>(m, "OGDFError", PyExc_Exception);

    // PyErr_NewException accepts a tuple of bases, which is how these end up
    // being both an OGDFError and the matching builtin.
    nb::object value_bases = nb::make_tuple(base, nb::handle(PyExc_ValueError));
    nb::object runtime_bases =
        nb::make_tuple(base, nb::handle(PyExc_RuntimeError));

    nb::object precondition =
        nb::exception<PreconditionError>(m, "PreconditionError", value_bases);
    nb::exception<InvalidGraphError>(m, "InvalidGraphError", precondition);
    nb::exception<UnsupportedFormatError>(m, "UnsupportedFormatError",
                                          value_bases);
    nb::exception<AlgorithmError>(m, "AlgorithmError", runtime_bases);
}
