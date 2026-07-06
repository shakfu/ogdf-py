// Layout algorithms and the enums that configure them.

#include "bindings.h"

#include <cmath>

#include <ogdf/basic/GraphAttributes.h>
#include <ogdf/basic/geometry.h>
#include <ogdf/energybased/FMMMLayout.h>
#include <ogdf/energybased/GEMLayout.h>
#include <ogdf/energybased/PivotMDS.h>
#include <ogdf/energybased/SpringEmbedderKK.h>
#include <ogdf/energybased/StressMinimization.h>
#include <ogdf/energybased/fmmm/FMMMOptions.h>
#include <ogdf/layered/SugiyamaLayout.h>
#include <ogdf/misclayout/CircularLayout.h>
#include <ogdf/orthogonal/OrthoLayout.h>
#include <ogdf/planarity/PlanarizationLayout.h>
#include <ogdf/planarlayout/SchnyderLayout.h>
#include <ogdf/tree/TreeLayout.h>

using namespace ogdf;
using namespace nb::literals;

// GEMLayout and SpringEmbedderKK refine an existing layout rather than build one
// from scratch; with the default all-zero coordinates they collapse (or produce
// NaNs). Seed distinct positions on a circle when no initial layout is present,
// while leaving any user-provided layout untouched.
static void seed_circle_if_degenerate(GraphAttributes& ga) {
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
        const double angle = 2.0 * M_PI * i / n;
        ga.x(v) = radius * std::cos(angle);
        ga.y(v) = radius * std::sin(angle);
        ++i;
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
}
