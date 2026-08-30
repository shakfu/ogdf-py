// Build provenance and capability reporting, consumed by `ogdf.about()`.
//
// Everything here is resolved at compile time (or from OGDF's own compiled-in
// configuration), so a diagnostic report describes the extension that is
// actually loaded rather than what the source tree currently says.

#include "bindings.h"

#include <nanobind/stl/string.h>

#include <ogdf/basic/basic.h>
#include <ogdf/basic/internal/config.h>
#include <ogdf/basic/internal/version.h>

#ifndef OGDFPY_VERSION
#    define OGDFPY_VERSION "unknown"
#endif
#ifndef OGDFPY_OGDF_TAG
#    define OGDFPY_OGDF_TAG "unknown"
#endif

using namespace ogdf;
using namespace nb::literals;

namespace {

// The compiler that produced this extension. Useful when a wheel misbehaves on
// a platform we cannot reproduce locally.
std::string compiler_id() {
#if defined(_MSC_VER)
    return "MSVC " + std::to_string(_MSC_VER);
#elif defined(__clang__)
    return "Clang " + std::string(__clang_version__);
#elif defined(__GNUC__)
    return "GCC " + std::to_string(__GNUC__) + "." +
           std::to_string(__GNUC_MINOR__) + "." +
           std::to_string(__GNUC_PATCHLEVEL__);
#else
    return "unknown";
#endif
}

}  // namespace

void register_meta(nb::module_& m) {
    m.def("build_info",
          []() {
              nb::dict d;
              d["package_version"] = OGDFPY_VERSION;
              d["ogdf_version"] = OGDF_VERSION;
              d["ogdf_tag"] = OGDFPY_OGDF_TAG;
              d["ogdf_system"] =
                  Configuration::toString(Configuration::whichSystem());
              d["ogdf_lp_solver"] =
                  Configuration::toString(Configuration::whichLPSolver());
              d["ogdf_memory_manager"] =
                  Configuration::toString(Configuration::whichMemoryManager());
#ifdef OGDF_DEBUG
              d["ogdf_debug_build"] = true;
#else
              d["ogdf_debug_build"] = false;
#endif
              d["compiler"] = compiler_id();
              d["cpp_standard"] = static_cast<long long>(__cplusplus);
              return d;
          },
          "Build provenance of the compiled extension: package version, OGDF "
          "version and pinned tag, OGDF's compiled-in configuration, and the "
          "compiler used. See `ogdf.about()` for the full report.");

    // OGDF draws all randomness from one process-wide engine, so seeding is a
    // global operation rather than a per-call argument. `ogdf.set_seed()` and
    // `ogdf.seeded()` wrap these; see the reproducibility docs.
    m.def("seed_random_engine", [](int seed) { ogdf::setSeed(seed); }, "seed"_a,
          "Seed OGDF's process-wide random engine. Every randomized generator, "
          "layout, and heuristic draws from it, so this makes them "
          "reproducible. Prefer `ogdf.set_seed()` / `ogdf.seeded()`, which "
          "wrap this and record the seed for `ogdf.provenance()`.");
    m.def("draw_random_seed", []() {
              return static_cast<long long>(ogdf::randomSeed());
          },
          "Draw a fresh seed value from OGDF's engine. Useful to pick a seed, "
          "record it, and then set it - the engine has no way to report the "
          "seed it is currently running from.");
}
