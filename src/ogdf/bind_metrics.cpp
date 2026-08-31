// Drawing-quality metrics computed from a laid-out GraphAttributes.
//
// These measure the *drawing*, not the graph: how many edges cross, how evenly
// long they are, how tightly nodes are packed, how faithfully the geometry
// reproduces graph distances. They exist so two layouts can be compared on
// numbers instead of by eye, and so a layout's quality can be regression-tested.
//
// Everything here is geometry over the coordinates OGDF produced, so the
// pairwise metrics are quadratic: crossings in the number of edges, overlap and
// stress in the number of nodes. That is fine for the thousands-of-nodes graphs
// people actually inspect, and documented on each function.

#include "bindings.h"
#include "errors.h"

#include <nanobind/stl/vector.h>

#include <algorithm>
#include <cmath>
#include <limits>
#include <vector>

#include <ogdf/basic/GraphAttributes.h>
#include <ogdf/basic/geometry.h>
#include <ogdf/graphalg/ShortestPathAlgorithms.h>

using namespace ogdf;
using namespace nb::literals;

namespace {

constexpr double kPi = 3.14159265358979323846;

// The drawn polyline of an edge: source point, bend points, target point.
// Layouts that route edges (orthogonal, planarization) put the interesting
// geometry in the bends, so a metric that ignored them would score those
// layouts as though their edges ran straight through everything.
std::vector<DPoint> polyline(const GraphAttributes& ga, edge e) {
    std::vector<DPoint> points;
    points.emplace_back(ga.x(e->source()), ga.y(e->source()));
    for (const DPoint& p : ga.bends(e)) {
        points.push_back(p);
    }
    points.emplace_back(ga.x(e->target()), ga.y(e->target()));
    return points;
}

// Graph-theoretic distances from one node, in edge hops. Unreachable nodes keep
// the -1 the array is initialised with, since bfs_SPSS only writes the nodes it
// actually reaches.
void hop_distances(const Graph& g, node source, NodeArray<int>& distance) {
    distance.init(g, -1);
    bfs_SPSS<int>(source, g, distance, 1);
}

}  // namespace

void register_metrics(nb::module_& m) {
    m.def("count_crossings",
          [](const GraphAttributes& ga) {
              const Graph& g = ga.constGraph();
              std::vector<edge> edges;
              std::vector<std::vector<DPoint>> lines;
              edges.reserve(static_cast<size_t>(g.numberOfEdges()));
              lines.reserve(static_cast<size_t>(g.numberOfEdges()));
              for (edge e : g.edges) {
                  edges.push_back(e);
                  lines.push_back(polyline(ga, e));
              }

              long long crossings = 0;
              std::vector<DPoint> shared;  // positions of shared endpoints
              for (size_t i = 0; i < lines.size(); ++i) {
                  for (size_t j = i + 1; j < lines.size(); ++j) {
                      // Two edges meeting at a node touch there but do not
                      // cross there. DSegment::intersection has an `endpoints`
                      // flag that looks like it handles this, but it tests the
                      // segment's *bounding rectangle*, which is degenerate for
                      // an axis-aligned segment - every point of a horizontal
                      // or vertical edge lies on its boundary, so passing false
                      // discards all of its intersections. That would report
                      // zero crossings for exactly the orthogonal and grid
                      // layouts this metric is most useful on. So intersect
                      // with endpoints included and exclude shared nodes here.
                      shared.clear();
                      for (node v : {edges[i]->source(), edges[i]->target()}) {
                          if (v == edges[j]->source() ||
                              v == edges[j]->target()) {
                              shared.emplace_back(ga.x(v), ga.y(v));
                          }
                      }
                      for (size_t a = 0; a + 1 < lines[i].size(); ++a) {
                          if (lines[i][a] == lines[i][a + 1]) {
                              continue;  // degenerate segment (e.g. a self-loop)
                          }
                          const DSegment s1(lines[i][a], lines[i][a + 1]);
                          for (size_t b = 0; b + 1 < lines[j].size(); ++b) {
                              if (lines[j][b] == lines[j][b + 1]) {
                                  continue;
                              }
                              const DSegment s2(lines[j][b], lines[j][b + 1]);
                              DPoint inter;
                              if (s1.intersection(s2, inter, true) !=
                                  IntersectionType::SinglePoint) {
                                  continue;  // Overlapping collinear or None
                              }
                              bool at_shared_node = false;
                              for (const DPoint& p : shared) {
                                  if (inter == p) {
                                      at_shared_node = true;
                                      break;
                                  }
                              }
                              if (!at_shared_node) {
                                  ++crossings;
                              }
                          }
                      }
                  }
              }
              return crossings;
          },
          "graph_attributes"_a,
          "Number of edge crossings in the drawing, counted over the drawn "
          "polylines so bends are respected. Two edges meeting at a shared node "
          "do not count as crossing there, but an endpoint touching another "
          "edge's interior does. Collinear overlapping edges (such as parallel "
          "edges drawn straight) are not counted. Quadratic in the number of "
          "edges. This measures the *drawing*; `crossing_number()` measures the "
          "graph, and the two agree only when the drawing is optimal.");

    m.def("edge_lengths",
          [](const GraphAttributes& ga) {
              std::vector<double> lengths;
              lengths.reserve(
                  static_cast<size_t>(ga.constGraph().numberOfEdges()));
              for (edge e : ga.constGraph().edges) {
                  const auto points = polyline(ga, e);
                  double total = 0.0;
                  for (size_t i = 0; i + 1 < points.size(); ++i) {
                      total += points[i].distance(points[i + 1]);
                  }
                  lengths.push_back(total);
              }
              return lengths;
          },
          "graph_attributes"_a,
          "The drawn length of every edge, in edge iteration order, measured "
          "along its polyline. Uniform edge lengths are a common readability "
          "goal, so the spread of these matters as much as the mean.");

    m.def("bounding_box",
          [](const GraphAttributes& ga) {
              const Graph& g = ga.constGraph();
              if (g.empty()) {
                  return nb::make_tuple(0.0, 0.0, 0.0, 0.0);
              }
              double min_x = std::numeric_limits<double>::max();
              double min_y = min_x;
              double max_x = std::numeric_limits<double>::lowest();
              double max_y = max_x;
              // Node boxes, not just centres - a drawing's extent includes the
              // shapes that will be rendered.
              for (node v : g.nodes) {
                  min_x = std::min(min_x, ga.x(v) - ga.width(v) / 2.0);
                  max_x = std::max(max_x, ga.x(v) + ga.width(v) / 2.0);
                  min_y = std::min(min_y, ga.y(v) - ga.height(v) / 2.0);
                  max_y = std::max(max_y, ga.y(v) + ga.height(v) / 2.0);
              }
              for (edge e : g.edges) {
                  for (const DPoint& p : ga.bends(e)) {
                      min_x = std::min(min_x, p.m_x);
                      max_x = std::max(max_x, p.m_x);
                      min_y = std::min(min_y, p.m_y);
                      max_y = std::max(max_y, p.m_y);
                  }
              }
              return nb::make_tuple(min_x, min_y, max_x, max_y);
          },
          "graph_attributes"_a,
          "The drawing's extent as (min_x, min_y, max_x, max_y), including "
          "node boxes and edge bend points. An empty graph gives all zeros.");

    m.def("node_overlaps",
          [](const GraphAttributes& ga) {
              const Graph& g = ga.constGraph();
              long long pairs = 0;
              double area = 0.0;
              std::vector<node> nodes;
              nodes.reserve(static_cast<size_t>(g.numberOfNodes()));
              for (node v : g.nodes) {
                  nodes.push_back(v);
              }
              for (size_t i = 0; i < nodes.size(); ++i) {
                  for (size_t j = i + 1; j < nodes.size(); ++j) {
                      const node u = nodes[i];
                      const node v = nodes[j];
                      const double dx =
                          std::min(ga.x(u) + ga.width(u) / 2.0,
                                   ga.x(v) + ga.width(v) / 2.0) -
                          std::max(ga.x(u) - ga.width(u) / 2.0,
                                   ga.x(v) - ga.width(v) / 2.0);
                      const double dy =
                          std::min(ga.y(u) + ga.height(u) / 2.0,
                                   ga.y(v) + ga.height(v) / 2.0) -
                          std::max(ga.y(u) - ga.height(u) / 2.0,
                                   ga.y(v) - ga.height(v) / 2.0);
                      if (dx > 0.0 && dy > 0.0) {
                          ++pairs;
                          area += dx * dy;
                      }
                  }
              }
              return nb::make_tuple(pairs, area);
          },
          "graph_attributes"_a,
          "Overlapping node boxes as (pair_count, total_overlap_area). Nodes "
          "are treated as axis-aligned rectangles of their width and height "
          "centred on their coordinates, so this is zero for a drawing whose "
          "node sizes were never set. Quadratic in the number of nodes.");

    m.def("min_angle",
          [](const GraphAttributes& ga) -> nb::object {
              const Graph& g = ga.constGraph();
              double smallest = std::numeric_limits<double>::max();
              bool found = false;
              std::vector<double> angles;
              for (node v : g.nodes) {
                  angles.clear();
                  for (adjEntry adj : v->adjEntries) {
                      const edge e = adj->theEdge();
                      if (e->isSelfLoop()) {
                          continue;  // no well-defined single direction
                      }
                      const auto points = polyline(ga, e);
                      // The first drawn segment leaving this node.
                      const DPoint& here =
                          (e->source() == v) ? points.front() : points.back();
                      const DPoint& next = (e->source() == v)
                                               ? points[1]
                                               : points[points.size() - 2];
                      const double dx = next.m_x - here.m_x;
                      const double dy = next.m_y - here.m_y;
                      if (dx == 0.0 && dy == 0.0) {
                          continue;  // coincident endpoints: no direction
                      }
                      angles.push_back(std::atan2(dy, dx));
                  }
                  if (angles.size() < 2) {
                      continue;
                  }
                  std::sort(angles.begin(), angles.end());
                  for (size_t i = 0; i + 1 < angles.size(); ++i) {
                      smallest = std::min(smallest, angles[i + 1] - angles[i]);
                      found = true;
                  }
                  // Close the cycle around the node.
                  smallest = std::min(
                      smallest, 2.0 * kPi - (angles.back() - angles.front()));
                  found = true;
              }
              if (!found) {
                  return nb::none();
              }
              return nb::cast(smallest);
          },
          "graph_attributes"_a,
          "The smallest angle, in radians, between two edges leaving the same "
          "node - the drawing's angular resolution. Larger is more legible; "
          "the best achievable at a node of degree d is 2*pi/d. Self-loops are "
          "skipped, and None is returned when no node has two or more "
          "non-loop edges.");

    m.def("stress",
          [](const GraphAttributes& ga, bool normalize) {
              const Graph& g = ga.constGraph();
              if (g.numberOfNodes() < 2) {
                  return 0.0;
              }
              // Accumulate over pairs one BFS row at a time: the full distance
              // matrix would be quadratic in memory for no benefit.
              //
              // With weight w_ij = 1 / d_ij^2, stress is
              //     sum_{i<j} w_ij * (s * ||p_i - p_j|| - d_ij)^2
              // where s is a uniform scale factor. A drawing can be scaled
              // arbitrarily without changing its quality, so `normalize` picks
              // the s that minimises the sum, making the metric comparable
              // across layouts that work at different scales.
              std::vector<node> nodes;
              nodes.reserve(static_cast<size_t>(g.numberOfNodes()));
              for (node v : g.nodes) {
                  nodes.push_back(v);
              }
              NodeArray<int> hops(g);
              double num = 0.0;  // sum w * d * e
              double den = 0.0;  // sum w * e^2
              std::vector<std::pair<double, double>> pairs;  // (w, e), d folded
              std::vector<double> targets;
              for (size_t i = 0; i < nodes.size(); ++i) {
                  hop_distances(g, nodes[i], hops);
                  for (size_t j = i + 1; j < nodes.size(); ++j) {
                      const int d = hops[nodes[j]];
                      if (d <= 0) {
                          continue;  // unreachable (-1) or coincident
                      }
                      const double target = static_cast<double>(d);
                      const double dx = ga.x(nodes[i]) - ga.x(nodes[j]);
                      const double dy = ga.y(nodes[i]) - ga.y(nodes[j]);
                      const double euclid = std::sqrt(dx * dx + dy * dy);
                      const double w = 1.0 / (target * target);
                      pairs.emplace_back(w, euclid);
                      targets.push_back(target);
                      num += w * target * euclid;
                      den += w * euclid * euclid;
                  }
              }
              if (pairs.empty()) {
                  return 0.0;
              }
              const double scale =
                  (normalize && den > 0.0) ? (num / den) : 1.0;
              double total = 0.0;
              for (size_t k = 0; k < pairs.size(); ++k) {
                  const double diff = scale * pairs[k].second - targets[k];
                  total += pairs[k].first * diff * diff;
              }
              return total;
          },
          "graph_attributes"_a, "normalize"_a = true,
          "Stress: how far the drawn distances stray from graph distances, as "
          "sum over node pairs of (drawn - hops)^2 / hops^2. Lower is better, "
          "and 0 means every pair is drawn exactly its hop count apart. "
          "Disconnected pairs are skipped. With `normalize` (the default) the "
          "drawing is first scaled by the factor that minimises the sum, so "
          "the value does not change when a layout is uniformly scaled and "
          "layouts working at different scales stay comparable. Quadratic in "
          "the number of nodes.");
}
