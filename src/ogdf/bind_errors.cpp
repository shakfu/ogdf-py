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

#include <nanobind/stl/string.h>

#include <ogdf/basic/exceptions.h>

#include <string>

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
    nb::object algorithm =
        nb::exception<AlgorithmError>(m, "AlgorithmError", runtime_bases);

    // ogdf::Exception derives privately from std::exception, so nanobind's
    // std::exception fallback cannot catch it and the error would surface as
    // an unknown C++ exception. Map OGDF's failures onto the taxonomy above.
    static nb::handle algorithm_type = algorithm.release();
    static nb::handle base_type = base.inc_ref();
    nb::register_exception_translator(
        [](const std::exception_ptr& p, void*) {
            try {
                std::rethrow_exception(p);
            } catch (const ogdf::AlgorithmFailureException& e) {
                const std::string msg =
                    "OGDF algorithm failure (code " +
                    std::to_string(static_cast<int>(e.exceptionCode())) + ")";
                PyErr_SetString(algorithm_type.ptr(), msg.c_str());
            } catch (const ogdf::Exception&) {
                PyErr_SetString(base_type.ptr(), "OGDF raised an internal error");
            }
        });

    // Test hook: lets the suite check the translator, since no bound call
    // reliably makes OGDF throw.
    m.def("_throw_for_test", [](const std::string& kind) {
        if (kind == "algorithm") {
            throw ogdf::AlgorithmFailureException(
                ogdf::AlgorithmFailureCode::Unknown, __FILE__, __LINE__);
        }
        throw ogdf::DynamicCastFailedException(__FILE__, __LINE__);
    });
}
