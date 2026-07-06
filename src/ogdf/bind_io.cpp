// File I/O: graph interchange formats (GML, GraphML, DOT, GEXF, GDF, TLP) and
// drawing output (SVG, TikZ).

#include "bindings.h"

#include <nanobind/stl/string.h>

#include <algorithm>
#include <cctype>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>

#include <ogdf/basic/GraphAttributes.h>
#include <ogdf/fileformats/GraphIO.h>

using namespace ogdf;
using namespace nb::literals;

namespace {

std::string lower_extension(const std::string& path) {
    const auto dot = path.find_last_of('.');
    std::string ext = (dot == std::string::npos) ? "" : path.substr(dot + 1);
    std::transform(ext.begin(), ext.end(), ext.begin(),
                   [](unsigned char c) { return std::tolower(c); });
    return ext;
}

}  // namespace

void register_io(nb::module_& m) {
    // Format readers/writers are stream-based in OGDF; these wrappers add
    // filename ergonomics.
    auto reader = [](bool (*fn)(GraphAttributes&, Graph&, std::istream&)) {
        return [fn](GraphAttributes& ga, Graph& g, const std::string& path) {
            std::ifstream is(path);
            return is.good() && fn(ga, g, is);
        };
    };
    auto writer = [](bool (*fn)(const GraphAttributes&, std::ostream&)) {
        return [fn](const GraphAttributes& ga, const std::string& path) {
            std::ofstream os(path);
            return os.good() && fn(ga, os);
        };
    };

    m.def("read_gml", reader(&GraphIO::readGML), "graph_attributes"_a,
          "graph"_a, "filename"_a, "Read a GML file into (attributes, graph).");
    m.def("write_gml", writer(&GraphIO::writeGML), "graph_attributes"_a,
          "filename"_a, "Write attributes to a GML file.");
    m.def("read_graphml", reader(&GraphIO::readGraphML), "graph_attributes"_a,
          "graph"_a, "filename"_a, "Read a GraphML file.");
    m.def("write_graphml", writer(&GraphIO::writeGraphML), "graph_attributes"_a,
          "filename"_a, "Write attributes to a GraphML file.");
    m.def("read_dot", reader(&GraphIO::readDOT), "graph_attributes"_a,
          "graph"_a, "filename"_a, "Read a DOT file.");
    m.def("write_dot", writer(&GraphIO::writeDOT), "graph_attributes"_a,
          "filename"_a, "Write attributes to a DOT file.");
    m.def("read_gexf", reader(&GraphIO::readGEXF), "graph_attributes"_a,
          "graph"_a, "filename"_a, "Read a GEXF (Gephi) file.");
    m.def("write_gexf", writer(&GraphIO::writeGEXF), "graph_attributes"_a,
          "filename"_a, "Write attributes to a GEXF (Gephi) file.");
    m.def("read_gdf", reader(&GraphIO::readGDF), "graph_attributes"_a,
          "graph"_a, "filename"_a, "Read a GDF (GUESS) file.");
    m.def("write_gdf", writer(&GraphIO::writeGDF), "graph_attributes"_a,
          "filename"_a, "Write attributes to a GDF (GUESS) file.");
    m.def("read_tlp", reader(&GraphIO::readTLP), "graph_attributes"_a,
          "graph"_a, "filename"_a, "Read a TLP (Tulip) file.");
    m.def("write_tlp", writer(&GraphIO::writeTLP), "graph_attributes"_a,
          "filename"_a, "Write attributes to a TLP (Tulip) file.");

    // Generic read/write with the format auto-detected from the extension.
    m.def("read",
          [](Graph& g, const std::string& path) {
              return GraphIO::read(g, path);
          },
          "graph"_a, "filename"_a,
          "Read a graph, auto-detecting the format from the file extension.");
    m.def("write",
          [](const GraphAttributes& ga, const std::string& path) {
              // OGDF asserts are compiled out, so writing attributes to a
              // format that only supports plain graphs (e.g. LEDA, Chaco)
              // dereferences a null writer and crashes. Restrict the generic
              // writer to the extensions that support attribute output.
              static const char* kSupported[] = {"gml",  "dot",  "gv",
                                                  "graphml", "gexf", "gdf",
                                                  "tlp",  "dl",   "rudy",
                                                  "svg"};
              const std::string ext = lower_extension(path);
              if (std::find(std::begin(kSupported), std::end(kSupported),
                            ext) == std::end(kSupported)) {
                  throw std::invalid_argument(
                      "write(): unsupported or attribute-incapable extension '." +
                      ext +
                      "'. Supported: gml, dot, gv, graphml, gexf, gdf, tlp, "
                      "dl, rudy, svg.");
              }
              return GraphIO::write(ga, path);
          },
          "graph_attributes"_a, "filename"_a,
          "Write attributes, choosing the format from the file extension. "
          "Raises ValueError for formats that cannot store attributes.");

    // --- drawing output --- //
    m.def("draw_svg",
          [](const GraphAttributes& ga, const std::string& path) {
              return GraphIO::drawSVG(ga, path);
          },
          "graph_attributes"_a, "filename"_a,
          "Write the drawing to an SVG file. Returns True on success.");
    m.def("to_svg",
          [](const GraphAttributes& ga) {
              std::ostringstream os;
              GraphIO::drawSVG(ga, os);
              return os.str();
          },
          "graph_attributes"_a, "Return the drawing as an SVG string.");
    m.def("draw_tikz",
          [](const GraphAttributes& ga, const std::string& path) {
              std::ofstream os(path);
              return os.good() && GraphIO::drawTikz(ga, os);
          },
          "graph_attributes"_a, "filename"_a,
          "Write the drawing as a TikZ (LaTeX/PGF) file.");
    m.def("to_tikz",
          [](const GraphAttributes& ga) {
              std::ostringstream os;
              GraphIO::drawTikz(ga, os);
              return os.str();
          },
          "graph_attributes"_a, "Return the drawing as a TikZ string.");
}
