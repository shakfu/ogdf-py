cmake_minimum_required(VERSION 3.15...3.31)
project(${SKBUILD_PROJECT_NAME} VERSION ${SKBUILD_PROJECT_VERSION} LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
find_package(nanobind CONFIG REQUIRED)
find_package(Threads REQUIRED)

# --- OGDF (prebuilt static libraries) ---------------------------------------
# OGDF is cloned at a pinned tag and built from source by
# scripts/bootstrap_ogdf.py, which produces the OGDF/COIN static libraries and
# the generated config header. We link those static libs into the extension.
set(OGDF_ROOT "${CMAKE_SOURCE_DIR}/thirdparty/ogdf")
set(OGDF_BUILD "${OGDF_ROOT}/build")

# Locate the prebuilt OGDF/COIN static libraries produced by
# scripts/bootstrap_ogdf.py. Search both the single-config location and the
# multi-config Release/ subdirectory (used by MSVC and Xcode), and match both
# the Unix (libOGDF.a) and MSVC (OGDF.lib) naming.
set(_ogdf_lib_dirs "${OGDF_BUILD}" "${OGDF_BUILD}/Release")
find_library(OGDF_LIBRARY NAMES OGDF libOGDF PATHS ${_ogdf_lib_dirs}
             NO_DEFAULT_PATH)

# If OGDF has not been built yet, bootstrap it automatically (clone the pinned
# tag + build from source), then search again. This lets `pip install` from an
# sdist work without a separate manual step. Uses the interpreter CMake found.
if(NOT OGDF_LIBRARY AND EXISTS "${CMAKE_SOURCE_DIR}/scripts/bootstrap_ogdf.py")
    message(STATUS "OGDF not built; running scripts/bootstrap_ogdf.py ...")
    execute_process(
        COMMAND "${Python_EXECUTABLE}"
                "${CMAKE_SOURCE_DIR}/scripts/bootstrap_ogdf.py"
        RESULT_VARIABLE _ogdf_bootstrap_result)
    if(NOT _ogdf_bootstrap_result EQUAL 0)
        message(FATAL_ERROR
            "OGDF bootstrap failed (exit ${_ogdf_bootstrap_result}).")
    endif()
    unset(OGDF_LIBRARY CACHE)
    find_library(OGDF_LIBRARY NAMES OGDF libOGDF PATHS ${_ogdf_lib_dirs}
                 NO_DEFAULT_PATH)
endif()

find_library(COIN_LIBRARY NAMES COIN libCOIN PATHS ${_ogdf_lib_dirs}
             NO_DEFAULT_PATH)

if(NOT OGDF_LIBRARY OR NOT COIN_LIBRARY)
    message(FATAL_ERROR
        "Prebuilt OGDF not found under ${OGDF_BUILD}.\n"
        "Run the bootstrap first:\n"
        "    python scripts/bootstrap_ogdf.py\n"
        "(or `make bootstrap`), which clones OGDF at a pinned tag and builds it.")
endif()

# Public headers plus the build-time generated config header
# (config_autogen.h lives under build/include/ogdf-release).
set(OGDF_INCLUDE_DIRS
    "${OGDF_ROOT}/include"
    "${OGDF_BUILD}/include/ogdf-release")

set(OGDF_LIBRARIES ${OGDF_LIBRARY} ${COIN_LIBRARY} Threads::Threads)

nanobind_add_module(_core
    src/ogdf/_core.cpp
    src/ogdf/bind_graph.cpp
    src/ogdf/bind_layouts.cpp
    src/ogdf/bind_algorithms.cpp
    src/ogdf/bind_io.cpp
    src/ogdf/bind_generators.cpp)

target_include_directories(_core PRIVATE ${OGDF_INCLUDE_DIRS})
target_link_libraries(_core PRIVATE ${OGDF_LIBRARIES})

if(MSVC)
    target_compile_options(_core PRIVATE /W4)
else()
    target_compile_options(_core PRIVATE -Wall -Wextra)
endif()

install(TARGETS _core DESTINATION ogdf)

# Generate a type stub (_core.pyi) so the compiled module is typed for mypy and
# IDEs. nanobind imports the built module and introspects it at build time.
nanobind_add_stub(
    _core_stub
    MODULE _core
    OUTPUT _core.pyi
    PYTHON_PATH $<TARGET_FILE_DIR:_core>
    DEPENDS _core
)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/_core.pyi DESTINATION ogdf)

# Ship py.typed alongside the compiled module + stub. In an editable install the
# pure-Python files (including src/ogdf/py.typed) stay in the source tree, so
# without this the site-packages ogdf/ dir has _core.pyi but no py.typed marker,
# and mypy refuses to use the stub.
install(FILES ${CMAKE_SOURCE_DIR}/src/ogdf/py.typed DESTINATION ogdf)
