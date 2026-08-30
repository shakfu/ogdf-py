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
#
# For offline / locked-down / reproducible builds, point OGDF_PREBUILT_DIR at an
# OGDF tree that has already been built (it must contain include/ and a build/
# with the static libraries), either as -DOGDF_PREBUILT_DIR=... or via the
# environment. Setting OGDF_OFFLINE=1 disables the automatic git clone so a
# missing dependency fails fast with an explanation instead of hitting the
# network.
if(NOT OGDF_PREBUILT_DIR AND DEFINED ENV{OGDF_PREBUILT_DIR})
    set(OGDF_PREBUILT_DIR "$ENV{OGDF_PREBUILT_DIR}")
endif()

if(OGDF_PREBUILT_DIR)
    set(OGDF_ROOT "${OGDF_PREBUILT_DIR}")
    if(NOT EXISTS "${OGDF_ROOT}/include/ogdf")
        message(FATAL_ERROR
            "OGDF_PREBUILT_DIR=${OGDF_ROOT} does not look like an OGDF tree "
            "(no include/ogdf). Point it at the root of a built OGDF checkout.")
    endif()
    message(STATUS "Using prebuilt OGDF from ${OGDF_ROOT}")
else()
    set(OGDF_ROOT "${CMAKE_SOURCE_DIR}/thirdparty/ogdf")
endif()
set(OGDF_BUILD "${OGDF_ROOT}/build")

# The pinned OGDF tag, kept in one place (scripts/ogdf-tag.txt) so the bootstrap
# script and the compiled-in value reported by ogdf.about() cannot drift apart.
set(OGDF_PINNED_TAG "unknown")
if(EXISTS "${CMAKE_SOURCE_DIR}/scripts/ogdf-tag.txt")
    file(READ "${CMAKE_SOURCE_DIR}/scripts/ogdf-tag.txt" OGDF_PINNED_TAG)
    string(STRIP "${OGDF_PINNED_TAG}" OGDF_PINNED_TAG)
endif()

# Locate the prebuilt OGDF/COIN static libraries produced by
# scripts/bootstrap_ogdf.py. Search both the single-config location and the
# multi-config Release/ subdirectory (used by MSVC and Xcode), and match both
# the Unix (libOGDF.a) and MSVC (OGDF.lib) naming.
set(_ogdf_lib_dirs "${OGDF_BUILD}" "${OGDF_BUILD}/Release")
find_library(OGDF_LIBRARY NAMES OGDF libOGDF PATHS ${_ogdf_lib_dirs}
             NO_DEFAULT_PATH)

# If OGDF has not been built yet, bootstrap it automatically (fetch the pinned
# tag + build from source), then search again. This lets `pip install` from an
# sdist work without a separate manual step. Uses the interpreter CMake found.
# Skipped when a prebuilt tree was supplied explicitly.
set(_ogdf_offline OFF)
if(DEFINED ENV{OGDF_OFFLINE} AND NOT "$ENV{OGDF_OFFLINE}" STREQUAL "0")
    set(_ogdf_offline ON)
endif()

if(NOT OGDF_LIBRARY AND NOT OGDF_PREBUILT_DIR
   AND EXISTS "${CMAKE_SOURCE_DIR}/scripts/bootstrap_ogdf.py")
    message(STATUS "OGDF not built; running scripts/bootstrap_ogdf.py ...")
    execute_process(
        COMMAND "${Python_EXECUTABLE}"
                "${CMAKE_SOURCE_DIR}/scripts/bootstrap_ogdf.py"
        RESULT_VARIABLE _ogdf_bootstrap_result)
    if(NOT _ogdf_bootstrap_result EQUAL 0)
        message(FATAL_ERROR
            "OGDF bootstrap failed (exit ${_ogdf_bootstrap_result}).\n"
            "The bootstrap output above names the failing stage (source fetch, "
            "CMake configuration, or compilation). Building OGDF from source "
            "needs git, CMake >= 3.15, a C++17 compiler, network access, and "
            "roughly 2 GB of free disk space.\n"
            "For an offline build, vendor the source and set OGDF_ARCHIVE or "
            "OGDF_SOURCE_DIR, or build OGDF separately and configure this "
            "project with -DOGDF_PREBUILT_DIR=/path/to/ogdf.")
    endif()
    unset(OGDF_LIBRARY CACHE)
    find_library(OGDF_LIBRARY NAMES OGDF libOGDF PATHS ${_ogdf_lib_dirs}
                 NO_DEFAULT_PATH)
endif()

find_library(COIN_LIBRARY NAMES COIN libCOIN PATHS ${_ogdf_lib_dirs}
             NO_DEFAULT_PATH)

# Name the specific missing piece: OGDF and COIN are built by the same command,
# so having one but not the other means a partial or mismatched build tree.
if(NOT OGDF_LIBRARY OR NOT COIN_LIBRARY)
    set(_ogdf_missing "")
    if(NOT OGDF_LIBRARY)
        list(APPEND _ogdf_missing "OGDF")
    endif()
    if(NOT COIN_LIBRARY)
        list(APPEND _ogdf_missing "COIN")
    endif()
    string(REPLACE ";" " and " _ogdf_missing "${_ogdf_missing}")
    if(OGDF_PREBUILT_DIR)
        message(FATAL_ERROR
            "Prebuilt ${_ogdf_missing} static librar(y/ies) not found under "
            "${OGDF_BUILD}.\n"
            "OGDF_PREBUILT_DIR must point at an OGDF tree that has already been "
            "built with OGDF_LIBRARY_TARGETS_ONLY=ON and "
            "CMAKE_POSITION_INDEPENDENT_CODE=ON.")
    elseif(_ogdf_offline)
        message(FATAL_ERROR
            "Prebuilt ${_ogdf_missing} static librar(y/ies) not found under "
            "${OGDF_BUILD}, and OGDF_OFFLINE is set so no source was fetched.\n"
            "Vendor the OGDF source and run:\n"
            "    python scripts/bootstrap_ogdf.py --archive /path/to/ogdf-src.tar.gz\n"
            "or configure with -DOGDF_PREBUILT_DIR=/path/to/prebuilt/ogdf.")
    else()
        message(FATAL_ERROR
            "Prebuilt ${_ogdf_missing} static librar(y/ies) not found under "
            "${OGDF_BUILD}.\n"
            "Run the bootstrap first:\n"
            "    python scripts/bootstrap_ogdf.py\n"
            "(or `make bootstrap`), which fetches OGDF at the pinned tag "
            "(${OGDF_PINNED_TAG}) and builds it.")
    endif()
endif()

# Public headers plus the build-time generated config header
# (config_autogen.h lives under build/include/ogdf-release).
set(OGDF_INCLUDE_DIRS
    "${OGDF_ROOT}/include"
    "${OGDF_BUILD}/include/ogdf-release")

set(OGDF_LIBRARIES ${OGDF_LIBRARY} ${COIN_LIBRARY} Threads::Threads)

nanobind_add_module(_core
    src/ogdf/_core.cpp
    src/ogdf/bind_errors.cpp
    src/ogdf/bind_graph.cpp
    src/ogdf/bind_layouts.cpp
    src/ogdf/bind_algorithms.cpp
    src/ogdf/bind_io.cpp
    src/ogdf/bind_generators.cpp
    src/ogdf/bind_meta.cpp)

target_include_directories(_core PRIVATE ${OGDF_INCLUDE_DIRS})

# Build provenance reported by ogdf.about(): the package version and the
# pinned OGDF tag the linked static libraries were built from.
target_compile_definitions(_core PRIVATE
    OGDFPY_VERSION="${PROJECT_VERSION}"
    OGDFPY_OGDF_TAG="${OGDF_PINNED_TAG}")
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
