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
# scripts/bootstrap_ogdf.sh, which produces libOGDF.a / libCOIN.a and the
# generated config header. We link those static libs into the extension.
set(OGDF_ROOT "${CMAKE_SOURCE_DIR}/thirdparty/ogdf")
set(OGDF_BUILD "${OGDF_ROOT}/build")

# If OGDF has not been built yet, try to bootstrap it automatically (clone the
# pinned tag + build from source). This lets `pip install` from an sdist work
# without a separate manual step. Windows is not supported by the bash script.
if(NOT EXISTS "${OGDF_BUILD}/libOGDF.a"
   AND EXISTS "${CMAKE_SOURCE_DIR}/scripts/bootstrap_ogdf.sh"
   AND NOT WIN32)
    message(STATUS "OGDF not built; running scripts/bootstrap_ogdf.sh ...")
    execute_process(
        COMMAND bash "${CMAKE_SOURCE_DIR}/scripts/bootstrap_ogdf.sh"
        RESULT_VARIABLE _ogdf_bootstrap_result)
    if(NOT _ogdf_bootstrap_result EQUAL 0)
        message(FATAL_ERROR
            "OGDF bootstrap failed (exit ${_ogdf_bootstrap_result}).")
    endif()
endif()

if(NOT EXISTS "${OGDF_BUILD}/libOGDF.a")
    message(FATAL_ERROR
        "Prebuilt OGDF not found at ${OGDF_BUILD}/libOGDF.a.\n"
        "Run the bootstrap script first:\n"
        "    scripts/bootstrap_ogdf.sh\n"
        "(or `make bootstrap`), which clones OGDF at a pinned tag and builds it.")
endif()

# Public headers plus the build-time generated config header
# (config_autogen.h lives under build/include/ogdf-release).
set(OGDF_INCLUDE_DIRS
    "${OGDF_ROOT}/include"
    "${OGDF_BUILD}/include/ogdf-release")

set(OGDF_LIBRARIES
    "${OGDF_BUILD}/libOGDF.a"
    "${OGDF_BUILD}/libCOIN.a"
    Threads::Threads)

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
