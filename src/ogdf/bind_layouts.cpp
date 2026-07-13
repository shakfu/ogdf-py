// Layout algorithms and the enums that configure them.

#include "bindings.h"

#include <cmath>
#include <stdexcept>
#include <string>

#include <ogdf/basic/GraphAttributes.h>
#include <ogdf/basic/geometry.h>
#include <ogdf/basic/simple_graph_alg.h>
#include <ogdf/energybased/FMMMLayout.h>
#include <ogdf/energybased/GEMLayout.h>
#include <ogdf/energybased/MultilevelLayout.h>
#include <ogdf/energybased/PivotMDS.h>
#include <ogdf/energybased/SpringEmbedderKK.h>
#include <ogdf/energybased/StressMinimization.h>
#include <ogdf/energybased/TutteLayout.h>
#include <ogdf/energybased/fmmm/FMMMOptions.h>
#include <ogdf/energybased/multilevel_mixer/ModularMultilevelMixer.h>
#include <ogdf/layered/SugiyamaLayout.h>
#include <ogdf/misclayout/BalloonLayout.h>
#include <ogdf/misclayout/CircularLayout.h>
#include <ogdf/misclayout/LinearLayout.h>
#include <ogdf/orthogonal/OrthoLayout.h>
#include <ogdf/planarity/PlanarizationLayout.h>
#include <ogdf/planarlayout/FPPLayout.h>
#include <ogdf/planarlayout/MixedModelLayout.h>
#include <ogdf/planarlayout/PlanarDrawLayout.h>
#include <ogdf/planarlayout/PlanarStraightLayout.h>
#include <ogdf/planarlayout/SchnyderLayout.h>
#include <ogdf/tree/RadialTreeLayout.h>
#include <ogdf/tree/TreeLayout.h>
#include <ogdf/upward/DominanceLayout.h>
#include <ogdf/upward/VisibilityLayout.h>

using namespace ogdf;
using namespace nb::literals;

// GEMLayout and SpringEmbedderKK refine an existing layout rather than build one
// from scratch; with the default all-zero coordinates they collapse (or produce
// NaNs). Seed distinct positions on a circle when no initial layout is present,
// while leaving any user-provided layout untouched.
static void seed_circle_if_degenerate(GraphAttributes& ga) {
    // M_PI is non-standard and undefined on MSVC, so use an explicit constant.
    constexpr double kPi = 3.14159265358979323846;
    const Graph& g = ga.constGraph();
    for (node v : g.nodes) {
        if (ga.x(v) != 0.0 || ga.y(v) != 0.0) {
            return;  // an initial layout already exists
        }
    }
    const int n = g.numberOfNodes();
    if (n == 0) {
        return;
    }
    const double radius = 10.0 * n;
    int i = 0;
    for (node v : g.nodes) {
        const double angle = 2.0 * kPi * i / n;
        ga.x(v) = radius * std::cos(angle);
        ga.y(v) = radius * std::sin(angle);
        ++i;
    }
}

// The planar grid layouts (FPP, PlanarStraight, PlanarDraw, MixedModel) require
// a simple planar graph with at least 3 nodes; OGDF augments connectivity
// internally but assumes planarity and simplicity. Guard here so bad input
// raises a clear Python error instead of tripping an assertion or running into
// undefined behaviour in a release build.
static void require_simple_planar(const GraphAttributes& ga, const char* name) {
    const Graph& g = ga.constGraph();
    if (g.numberOfNodes() < 3) {
        throw std::invalid_argument(std::string(name) +
                                    " requires at least 3 nodes");
    }
    if (!isSimpleUndirected(g)) {
        throw std::invalid_argument(std::string(name) +
                                    " requires a simple graph (no self-loops or "
                                    "parallel edges)");
    }
    if (!isPlanar(g)) {
        throw std::invalid_argument(std::string(name) +
                                    " requires a planar graph");
    }
}

void register_layouts(nb::module_& m) {
    // --- enums used by layout configuration --- //
    nb::enum_<Orientation>(m, "Orientation")
        .value("TOP_TO_BOTTOM", Orientation::topToBottom)
        .value("BOTTOM_TO_TOP", Orientation::bottomToTop)
        .value("LEFT_TO_RIGHT", Orientation::leftToRight)
        .value("RIGHT_TO_LEFT", Orientation::rightToLeft);

    nb::enum_<TreeLayout::RootSelectionType>(m, "RootSelection")
        .value("SOURCE", TreeLayout::RootSelectionType::Source)
        .value("BY_COORD", TreeLayout::RootSelectionType::ByCoord);

    nb::enum_<FMMMOptions::QualityVsSpeed>(m, "QualityVsSpeed")
        .value("GORGEOUS_AND_EFFICIENT",
               FMMMOptions::QualityVsSpeed::GorgeousAndEfficient)
        .value("BEAUTIFUL_AND_FAST",
               FMMMOptions::QualityVsSpeed::BeautifulAndFast)
        .value("NICE_AND_INCREDIBLE_SPEED",
               FMMMOptions::QualityVsSpeed::NiceAndIncredibleSpeed);

    // --- layouts --- //
    nb::class_<SugiyamaLayout>(m, "SugiyamaLayout")
        .def(nb::init<>())
        .def("call", [](SugiyamaLayout& s, GraphAttributes& g) { s.call(g); },
             "graph_attributes"_a, "Compute a layered (Sugiyama) layout.")
        .def("set_fails", [](SugiyamaLayout& s, int n) { s.fails(n); }, "n"_a)
        .def("set_runs", [](SugiyamaLayout& s, int n) { s.runs(n); }, "n"_a)
        .def("set_transpose",
             [](SugiyamaLayout& s, bool b) { s.transpose(b); }, "value"_a)
        .def("set_arrange_ccs",
             [](SugiyamaLayout& s, bool b) { s.arrangeCCs(b); }, "value"_a);

    nb::class_<FMMMLayout>(m, "FMMMLayout")
        .def(nb::init<>())
        .def("call", [](FMMMLayout& f, GraphAttributes& g) { f.call(g); },
             "graph_attributes"_a, "Compute a force-directed (FMMM) layout.")
        .def("set_unit_edge_length",
             [](FMMMLayout& f, double x) { f.unitEdgeLength(x); }, "value"_a)
        .def("set_use_high_level_options",
             [](FMMMLayout& f, bool b) { f.useHighLevelOptions(b); }, "value"_a)
        .def("set_new_initial_placement",
             [](FMMMLayout& f, bool b) { f.newInitialPlacement(b); }, "value"_a)
        .def("set_fixed_iterations",
             [](FMMMLayout& f, int n) { f.fixedIterations(n); }, "n"_a)
        .def("set_rand_seed", [](FMMMLayout& f, int n) { f.randSeed(n); },
             "seed"_a)
        .def("set_quality_versus_speed",
             [](FMMMLayout& f, FMMMOptions::QualityVsSpeed q) {
                 f.qualityVersusSpeed(q);
             },
             "quality"_a);

    nb::class_<PlanarizationLayout>(m, "PlanarizationLayout")
        .def(nb::init<>())
        .def("call",
             [](PlanarizationLayout& p, GraphAttributes& g) { p.call(g); },
             "graph_attributes"_a, "Compute a planarization-based layout.")
        .def("use_orthogonal_layout",
             [](PlanarizationLayout& p, double separation) {
                 auto* ortho = new OrthoLayout();
                 ortho->separation(separation);
                 p.setPlanarLayouter(ortho);
             },
             "separation"_a = 40.0,
             "Use an orthogonal (right-angle) planar layouter.");

    nb::class_<TreeLayout>(m, "TreeLayout")
        .def(nb::init<>())
        .def("call", [](TreeLayout& t, GraphAttributes& g) { t.call(g); },
             "graph_attributes"_a,
             "Compute a tree layout (requires a tree/forest).")
        .def("set_sibling_distance",
             [](TreeLayout& t, double x) { t.siblingDistance(x); }, "value"_a)
        .def("set_level_distance",
             [](TreeLayout& t, double x) { t.levelDistance(x); }, "value"_a)
        .def("set_orthogonal_layout",
             [](TreeLayout& t, bool b) { t.orthogonalLayout(b); }, "value"_a)
        .def("set_orientation",
             [](TreeLayout& t, Orientation o) { t.orientation(o); },
             "orientation"_a)
        .def("set_root_selection",
             [](TreeLayout& t, TreeLayout::RootSelectionType r) {
                 t.rootSelection(r);
             },
             "selection"_a);

    nb::class_<CircularLayout>(m, "CircularLayout")
        .def(nb::init<>())
        .def("call", [](CircularLayout& c, GraphAttributes& g) { c.call(g); },
             "graph_attributes"_a, "Compute a circular layout.")
        .def("set_min_dist_circle",
             [](CircularLayout& c, double x) { c.minDistCircle(x); }, "value"_a)
        .def("set_min_dist_sibling",
             [](CircularLayout& c, double x) { c.minDistSibling(x); },
             "value"_a);

    nb::class_<StressMinimization>(m, "StressMinimization")
        .def(nb::init<>())
        .def("call",
             [](StressMinimization& s, GraphAttributes& g) { s.call(g); },
             "graph_attributes"_a,
             "Compute a stress-minimization (MDS-style) layout.")
        .def("set_iterations",
             [](StressMinimization& s, int n) { s.setIterations(n); }, "n"_a)
        .def("set_edge_costs",
             [](StressMinimization& s, double x) { s.setEdgeCosts(x); },
             "value"_a)
        .def("set_has_initial_layout",
             [](StressMinimization& s, bool b) { s.hasInitialLayout(b); },
             "value"_a)
        .def("set_layout_components_separately",
             [](StressMinimization& s, bool b) {
                 s.layoutComponentsSeparately(b);
             },
             "value"_a);

    nb::class_<PivotMDS>(m, "PivotMDS")
        .def(nb::init<>())
        .def("call", [](PivotMDS& p, GraphAttributes& g) { p.call(g); },
             "graph_attributes"_a, "Compute a pivot-MDS layout (fast MDS).")
        .def("set_number_of_pivots",
             [](PivotMDS& p, int n) { p.setNumberOfPivots(n); }, "n"_a)
        .def("set_edge_costs",
             [](PivotMDS& p, double x) { p.setEdgeCosts(x); }, "value"_a);

    nb::class_<GEMLayout>(m, "GEMLayout")
        .def(nb::init<>())
        .def("call",
             [](GEMLayout& l, GraphAttributes& g) {
                 seed_circle_if_degenerate(g);
                 l.call(g);
             },
             "graph_attributes"_a, "Compute a GEM force-directed layout.")
        .def("set_number_of_rounds",
             [](GEMLayout& l, int n) { l.numberOfRounds(n); }, "n"_a)
        .def("set_desired_length",
             [](GEMLayout& l, double x) { l.desiredLength(x); }, "value"_a)
        .def("set_min_dist_cc",
             [](GEMLayout& l, double x) { l.minDistCC(x); }, "value"_a)
        .def("set_page_ratio",
             [](GEMLayout& l, double x) { l.pageRatio(x); }, "value"_a);

    // Kamada-Kawai spring embedder. Requires a connected graph.
    nb::class_<SpringEmbedderKK>(m, "SpringEmbedderKK")
        .def(nb::init<>())
        .def("call",
             [](SpringEmbedderKK& s, GraphAttributes& g) {
                 seed_circle_if_degenerate(g);
                 s.call(g);
             },
             "graph_attributes"_a,
             "Compute a Kamada-Kawai layout (requires a connected graph).")
        .def("set_use_layout",
             [](SpringEmbedderKK& s, bool b) { s.setUseLayout(b); }, "value"_a)
        .def("set_max_global_iterations",
             [](SpringEmbedderKK& s, int n) { s.setMaxGlobalIterations(n); },
             "n"_a)
        .def("set_stop_tolerance",
             [](SpringEmbedderKK& s, double x) { s.setStopTolerance(x); },
             "value"_a)
        .def("set_desired_length",
             [](SpringEmbedderKK& s, double x) { s.setDesLength(x); },
             "value"_a);

    // Straight-line grid drawing of a planar graph. Requires the graph to be
    // planar, simple, and to have at least 3 nodes.
    nb::class_<SchnyderLayout>(m, "SchnyderLayout")
        .def(nb::init<>())
        .def("call", [](SchnyderLayout& s, GraphAttributes& g) { s.call(g); },
             "graph_attributes"_a,
             "Compute a Schnyder straight-line planar grid layout (requires a "
             "simple planar graph with at least 3 nodes).");

    // Straight-line planar grid drawing (de Fraysseix, Pach, Pollack). Like
    // Schnyder, draws a simple planar graph without crossings on an integer
    // grid.
    nb::class_<FPPLayout>(m, "FPPLayout")
        .def(nb::init<>())
        .def("call",
             [](FPPLayout& l, GraphAttributes& g) {
                 require_simple_planar(g, "FPPLayout");
                 l.call(g);
             },
             "graph_attributes"_a,
             "Compute a de Fraysseix-Pach-Pollack straight-line planar grid "
             "layout (requires a simple planar graph with at least 3 nodes).")
        .def("set_separation",
             [](FPPLayout& l, double x) { l.separation(x); }, "value"_a,
             "Minimum distance between nodes.");

    // Planar straight-line drawing with an augmentation/shelling-order pipeline.
    nb::class_<PlanarStraightLayout>(m, "PlanarStraightLayout")
        .def(nb::init<>())
        .def("call",
             [](PlanarStraightLayout& l, GraphAttributes& g) {
                 require_simple_planar(g, "PlanarStraightLayout");
                 l.call(g);
             },
             "graph_attributes"_a,
             "Compute a straight-line planar grid layout (requires a simple "
             "planar graph with at least 3 nodes).")
        .def("set_separation",
             [](PlanarStraightLayout& l, double x) { l.separation(x); },
             "value"_a, "Minimum distance between nodes.")
        .def("set_size_optimization",
             [](PlanarStraightLayout& l, bool b) { l.sizeOptimization(b); },
             "value"_a, "Try to reduce the grid size.")
        .def("set_base_ratio",
             [](PlanarStraightLayout& l, double x) { l.baseRatio(x); },
             "value"_a, "Fraction of external-face nodes placed on the base "
             "line.");

    // Planar straight-line drawing tuned for a more balanced aspect ratio.
    nb::class_<PlanarDrawLayout>(m, "PlanarDrawLayout")
        .def(nb::init<>())
        .def("call",
             [](PlanarDrawLayout& l, GraphAttributes& g) {
                 require_simple_planar(g, "PlanarDrawLayout");
                 l.call(g);
             },
             "graph_attributes"_a,
             "Compute a straight-line planar grid layout (requires a simple "
             "planar graph with at least 3 nodes).")
        .def("set_separation",
             [](PlanarDrawLayout& l, double x) { l.separation(x); }, "value"_a,
             "Minimum distance between nodes.")
        .def("set_size_optimization",
             [](PlanarDrawLayout& l, bool b) { l.sizeOptimization(b); },
             "value"_a, "Try to reduce the grid size.")
        .def("set_base_ratio",
             [](PlanarDrawLayout& l, double x) { l.baseRatio(x); }, "value"_a,
             "Fraction of external-face nodes placed on the base line.");

    // Mixed-model planar layout: orthogonal-style routing with nodes drawn as
    // boxes. Produces higher-quality planar drawings than the pure grid
    // algorithms.
    nb::class_<MixedModelLayout>(m, "MixedModelLayout")
        .def(nb::init<>())
        .def("call",
             [](MixedModelLayout& l, GraphAttributes& g) {
                 require_simple_planar(g, "MixedModelLayout");
                 l.call(g);
             },
             "graph_attributes"_a,
             "Compute a mixed-model planar layout (requires a simple planar "
             "graph with at least 3 nodes).")
        .def("set_separation",
             [](MixedModelLayout& l, double x) { l.separation(x); }, "value"_a,
             "Minimum distance between nodes.");

    // Radial tree drawing (concentric levels). Requires a tree.
    nb::enum_<RadialTreeLayout::RootSelectionType>(m, "RadialRootSelection")
        .value("SOURCE", RadialTreeLayout::RootSelectionType::Source)
        .value("SINK", RadialTreeLayout::RootSelectionType::Sink)
        .value("CENTER", RadialTreeLayout::RootSelectionType::Center);

    nb::class_<RadialTreeLayout>(m, "RadialTreeLayout")
        .def(nb::init<>())
        .def("call", [](RadialTreeLayout& l, GraphAttributes& g) { l.call(g); },
             "graph_attributes"_a,
             "Compute a radial tree layout (requires a tree).")
        .def("set_level_distance",
             [](RadialTreeLayout& l, double x) { l.levelDistance(x); },
             "value"_a)
        .def("set_root_selection",
             [](RadialTreeLayout& l, RadialTreeLayout::RootSelectionType r) {
                 l.rootSelection(r);
             },
             "selection"_a);

    // Arc diagram: nodes on a line, edges drawn as semicircular arcs.
    nb::class_<LinearLayout>(m, "LinearLayout")
        .def(nb::init<>())
        .def("call", [](LinearLayout& l, GraphAttributes& g) { l.call(g); },
             "graph_attributes"_a,
             "Compute a linear (arc-diagram) layout.");

    // Tutte barycentric embedding: convex straight-line planar drawing.
    // Requires a triconnected (planar) graph.
    nb::class_<TutteLayout>(m, "TutteLayout")
        .def(nb::init<>())
        .def("call", [](TutteLayout& l, GraphAttributes& g) { l.call(g); },
             "graph_attributes"_a,
             "Compute a Tutte barycentric convex planar layout (requires a "
             "triconnected planar graph).");

    // Upward drawings for directed acyclic graphs. Both internally planarize
    // the input to an upward-planar representation.
    nb::class_<DominanceLayout>(m, "DominanceLayout")
        .def(nb::init<>())
        .def("call", [](DominanceLayout& l, GraphAttributes& g) { l.call(g); },
             "graph_attributes"_a,
             "Compute an upward dominance drawing (for a DAG).")
        .def("set_min_grid_distance",
             [](DominanceLayout& l, int d) { l.setMinGridDistance(d); },
             "value"_a);

    nb::class_<VisibilityLayout>(m, "VisibilityLayout")
        .def(nb::init<>())
        .def("call", [](VisibilityLayout& l, GraphAttributes& g) { l.call(g); },
             "graph_attributes"_a,
             "Compute an upward visibility drawing (for a DAG).")
        .def("set_min_grid_distance",
             [](VisibilityLayout& l, int d) { l.setMinGridDistance(d); },
             "value"_a);

    // Multilevel force-directed layout for large graphs. The default
    // constructor installs a complete pipeline (coarsening + placement +
    // single-level layout) and handles disconnected graphs.
    nb::class_<MultilevelLayout>(m, "MultilevelLayout")
        .def(nb::init<>())
        .def("call", [](MultilevelLayout& l, GraphAttributes& g) { l.call(g); },
             "graph_attributes"_a,
             "Compute a multilevel force-directed layout (suited to large "
             "graphs).");

    // The multilevel mixer engine (used inside MultilevelLayout). Works with
    // defaults, but does not split disconnected components.
    nb::class_<ModularMultilevelMixer>(m, "ModularMultilevelMixer")
        .def(nb::init<>())
        .def("call",
             [](ModularMultilevelMixer& l, GraphAttributes& g) { l.call(g); },
             "graph_attributes"_a,
             "Compute a multilevel layout via the modular mixer.")
        .def("set_layout_repeats",
             [](ModularMultilevelMixer& l, int n) { l.setLayoutRepeats(n); },
             "n"_a)
        .def("set_all_edge_lengths",
             [](ModularMultilevelMixer& l, double x) { l.setAllEdgeLengths(x); },
             "value"_a);

    // Balloon layout: subtrees drawn in enclosing circles. Requires a
    // connected graph (a spanning tree is computed internally).
    nb::class_<BalloonLayout>(m, "BalloonLayout")
        .def(nb::init<>())
        .def("call",
             [](BalloonLayout& l, GraphAttributes& g) {
                 if (!isConnected(g.constGraph())) {
                     throw std::invalid_argument(
                         "BalloonLayout requires a connected graph");
                 }
                 l.call(g);
             },
             "graph_attributes"_a,
             "Compute a balloon layout (requires a connected graph).")
        .def("set_even_angles",
             [](BalloonLayout& l, bool b) { l.setEvenAngles(b); }, "value"_a);
}
