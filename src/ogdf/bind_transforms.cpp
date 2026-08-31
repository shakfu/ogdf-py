// Coordinate transforms over a finished drawing.
//
// Layouts produce coordinates in whatever range suits their algorithm. Getting
// that drawing onto a page - centred, scaled, fitted, with disconnected pieces
// packed instead of piled on top of each other - is a separate concern, and one
// the caller previously had to do by hand.
//
// Every transform here moves edge bend points as well as node coordinates.
// Missing the bends would silently tear apart any drawing produced by a routing
// layout (orthogonal, planarization), whose geometry lives mostly in its bends.
// That is also why these are here rather than in Python: bends are only
// reachable from Python through add_bend/clear_bends, which cannot move one.

#include "bindings.h"
#include "errors.h"

#include <algorithm>
#include <limits>
#include <vector>

#include <ogdf/basic/GraphAttributes.h>
#include <ogdf/basic/geometry.h>
#include <ogdf/basic/simple_graph_alg.h>
#include <ogdf/packing/TileToRowsCCPacker.h>

using namespace ogdf;
using namespace nb::literals;

namespace {

struct Box {
    double min_x = std::numeric_limits<double>::max();
    double min_y = std::numeric_limits<double>::max();
    double max_x = std::numeric_limits<double>::lowest();
    double max_y = std::numeric_limits<double>::lowest();

    bool empty() const { return min_x > max_x; }
    double width() const { return empty() ? 0.0 : max_x - min_x; }
    double height() const { return empty() ? 0.0 : max_y - min_y; }

    void add_node(const GraphAttributes& ga, node v) {
        min_x = std::min(min_x, ga.x(v) - ga.width(v) / 2.0);
        max_x = std::max(max_x, ga.x(v) + ga.width(v) / 2.0);
        min_y = std::min(min_y, ga.y(v) - ga.height(v) / 2.0);
        max_y = std::max(max_y, ga.y(v) + ga.height(v) / 2.0);
    }

    void add_point(const DPoint& p) {
        min_x = std::min(min_x, p.m_x);
        max_x = std::max(max_x, p.m_x);
        min_y = std::min(min_y, p.m_y);
        max_y = std::max(max_y, p.m_y);
    }
};

void translate_all(GraphAttributes& ga, double dx, double dy) {
    const Graph& g = ga.constGraph();
    for (node v : g.nodes) {
        ga.x(v) += dx;
        ga.y(v) += dy;
    }
    for (edge e : g.edges) {
        for (DPoint& p : ga.bends(e)) {
            p.m_x += dx;
            p.m_y += dy;
        }
    }
}

// The drawing's extent after scaling coordinates by `s` about the origin.
// When node sizes do not scale, this is not simply s * extent: the boxes stay
// the same while their centres move, so the width is a max of linear functions
// minus a min of linear functions. It is still increasing in s, which is what
// lets fit_scale bisect on it.
Box extent_after_scale(const GraphAttributes& ga, double s,
                       bool scale_node_sizes) {
    const Graph& g = ga.constGraph();
    Box box;
    for (node v : g.nodes) {
        const double half_w =
            (scale_node_sizes ? ga.width(v) * s : ga.width(v)) / 2.0;
        const double half_h =
            (scale_node_sizes ? ga.height(v) * s : ga.height(v)) / 2.0;
        box.min_x = std::min(box.min_x, ga.x(v) * s - half_w);
        box.max_x = std::max(box.max_x, ga.x(v) * s + half_w);
        box.min_y = std::min(box.min_y, ga.y(v) * s - half_h);
        box.max_y = std::max(box.max_y, ga.y(v) * s + half_h);
    }
    for (edge e : g.edges) {
        for (const DPoint& p : ga.bends(e)) {
            box.add_point(DPoint(p.m_x * s, p.m_y * s));
        }
    }
    return box;
}

}  // namespace

void register_transforms(nb::module_& m) {
    m.def("translate_drawing",
          [](GraphAttributes& ga, double dx, double dy) {
              translate_all(ga, dx, dy);
          },
          "graph_attributes"_a, "dx"_a, "dy"_a,
          "Move every node and edge bend by (dx, dy). Prefer `translate()`.");

    m.def("scale_drawing",
          [](GraphAttributes& ga, double sx, double sy, double cx, double cy,
             bool scale_node_sizes) {
              const Graph& g = ga.constGraph();
              for (node v : g.nodes) {
                  ga.x(v) = cx + (ga.x(v) - cx) * sx;
                  ga.y(v) = cy + (ga.y(v) - cy) * sy;
                  if (scale_node_sizes) {
                      ga.width(v) *= sx;
                      ga.height(v) *= sy;
                  }
              }
              for (edge e : g.edges) {
                  for (DPoint& p : ga.bends(e)) {
                      p.m_x = cx + (p.m_x - cx) * sx;
                      p.m_y = cy + (p.m_y - cy) * sy;
                  }
              }
          },
          "graph_attributes"_a, "sx"_a, "sy"_a, "cx"_a, "cy"_a,
          "scale_node_sizes"_a,
          "Scale the drawing about the point (cx, cy). Prefer `scale()`.");

    m.def("fit_scale",
          [](const GraphAttributes& ga, double width, double height,
             bool scale_node_sizes) {
              if (width <= 0.0 || height <= 0.0) {
                  throw ogdfpy::PreconditionError(
                      "fit_scale: width and height must be positive");
              }
              const Box current = extent_after_scale(ga, 1.0, scale_node_sizes);
              if (current.empty()) {
                  return 1.0;  // nothing drawn
              }
              if (scale_node_sizes) {
                  // Everything scales together, so the extent scales exactly
                  // and the factor is closed-form.
                  const double sx = current.width() > 0.0
                                        ? width / current.width()
                                        : std::numeric_limits<double>::max();
                  const double sy = current.height() > 0.0
                                        ? height / current.height()
                                        : std::numeric_limits<double>::max();
                  const double s = std::min(sx, sy);
                  return (s == std::numeric_limits<double>::max()) ? 1.0 : s;
              }
              // Node boxes stay put while their centres move, so solve for the
              // largest factor that still fits. The extent is increasing in s,
              // so bisect. If even s = 0 overflows, the node boxes alone are
              // bigger than the target and nothing can be done by scaling.
              const Box collapsed = extent_after_scale(ga, 0.0, false);
              if (collapsed.width() > width || collapsed.height() > height) {
                  return 0.0;
              }
              double lo = 0.0;
              double hi = 1.0;
              auto fits = [&](double s) {
                  const Box b = extent_after_scale(ga, s, false);
                  return b.width() <= width && b.height() <= height;
              };
              // Grow an upper bound first; the caller may be enlarging.
              for (int i = 0; i < 60 && fits(hi); ++i) {
                  lo = hi;
                  hi *= 2.0;
              }
              for (int i = 0; i < 100; ++i) {
                  const double mid = (lo + hi) / 2.0;
                  if (fits(mid)) {
                      lo = mid;
                  } else {
                      hi = mid;
                  }
              }
              return lo;
          },
          "graph_attributes"_a, "width"_a, "height"_a, "scale_node_sizes"_a,
          "The largest uniform factor by which the drawing can be scaled and "
          "still fit in width x height. Prefer `fit_to_box()`.");

    m.def("tile_components",
          [](GraphAttributes& ga, double separation, double page_ratio) {
              if (separation < 0.0) {
                  throw ogdfpy::PreconditionError(
                      "tile_components: separation must not be negative");
              }
              if (page_ratio <= 0.0) {
                  throw ogdfpy::PreconditionError(
                      "tile_components: page_ratio must be positive");
              }
              const Graph& g = ga.constGraph();
              if (g.empty()) {
                  return 0;
              }
              NodeArray<int> component(g);
              const int count = connectedComponents(g, component);
              if (count <= 1) {
                  return count;  // nothing to pack
              }

              std::vector<Box> boxes(static_cast<size_t>(count));
              for (node v : g.nodes) {
                  boxes[static_cast<size_t>(component[v])].add_node(ga, v);
              }
              for (edge e : g.edges) {
                  Box& box = boxes[static_cast<size_t>(component[e->source()])];
                  for (const DPoint& p : ga.bends(e)) {
                      box.add_point(p);
                  }
              }

              // Hand the component sizes to OGDF's packer, padded by the
              // requested separation so neighbours do not touch.
              Array<DPoint> sizes(count);
              Array<DPoint> offsets(count);
              for (int c = 0; c < count; ++c) {
                  const Box& box = boxes[static_cast<size_t>(c)];
                  sizes[c] = DPoint(box.width() + separation,
                                    box.height() + separation);
              }
              TileToRowsCCPacker().call(sizes, offsets, page_ratio);

              // Move each component so its padded lower-left corner sits on the
              // offset the packer chose.
              std::vector<double> dx(static_cast<size_t>(count));
              std::vector<double> dy(static_cast<size_t>(count));
              for (int c = 0; c < count; ++c) {
                  const Box& box = boxes[static_cast<size_t>(c)];
                  dx[static_cast<size_t>(c)] =
                      offsets[c].m_x + separation / 2.0 - box.min_x;
                  dy[static_cast<size_t>(c)] =
                      offsets[c].m_y + separation / 2.0 - box.min_y;
              }
              for (node v : g.nodes) {
                  const size_t c = static_cast<size_t>(component[v]);
                  ga.x(v) += dx[c];
                  ga.y(v) += dy[c];
              }
              for (edge e : g.edges) {
                  const size_t c =
                      static_cast<size_t>(component[e->source()]);
                  for (DPoint& p : ga.bends(e)) {
                      p.m_x += dx[c];
                      p.m_y += dy[c];
                  }
              }
              return count;
          },
          "graph_attributes"_a, "separation"_a = 20.0, "page_ratio"_a = 1.0,
          "Arrange the connected components side by side so they no longer "
          "overlap, using OGDF's tile-to-rows packer. Returns the number of "
          "components; prefer `pack_components()`. `separation` is the gap "
          "left between them and "
          "`page_ratio` the desired width/height of the result. A connected "
          "graph is left untouched.");
}
