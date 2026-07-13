"""Visualize algorithm results by coloring nodes and edges."""

import random

from _common import gradient_color, output_dir, palette

import ogdf


def demo_components(out):
    """Three disconnected clusters, colored by connected component."""
    g = ogdf.Graph()
    for _ in range(3):
        nodes = [g.new_node() for _ in range(6)]
        for i in range(6):
            g.new_edge(nodes[i], nodes[(i + 1) % 6])

    comp = ogdf.NodeArrayInt(g)
    k = ogdf.connected_components(g, comp)

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.FMMMLayout().call(ga)
    colors = palette(k)
    for v in g.nodes():
        ga.set_fill_color(v, colors[comp[v]])

    path = out / "algo_components.svg"
    ogdf.draw_svg(ga, str(path))
    return f"{k} connected components -> {path.name}"


def demo_coloring(out):
    """Proper node coloring, one palette color per color class."""
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 30, 60)

    colors_arr = ogdf.NodeArrayInt(g)
    k = ogdf.node_coloring(g, colors_arr)

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.CircularLayout().call(ga)
    pal = palette(k)
    for v in g.nodes():
        ga.set_fill_color(v, pal[colors_arr[v]])

    path = out / "algo_coloring.svg"
    ogdf.draw_svg(ga, str(path))
    return f"proper coloring with {k} colors -> {path.name}"


def demo_shortest_paths(out):
    """Grid graph shaded by shortest-path distance from a corner node."""
    g = ogdf.Graph()
    ogdf.grid_graph(g, 7, 7)

    source = next(g.nodes())
    weight = ogdf.EdgeArrayDouble(g, 1.0)
    dist = ogdf.NodeArrayDouble(g)
    ogdf.dijkstra(g, weight, source, dist)

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.FMMMLayout().call(ga)
    d_max = max(dist[v] for v in g.nodes()) or 1.0
    for v in g.nodes():
        ga.set_fill_color(v, gradient_color(dist[v] / d_max))

    path = out / "algo_shortest_paths.svg"
    ogdf.draw_svg(ga, str(path))
    return f"shortest paths (max distance {d_max:.0f}) -> {path.name}"


def demo_mst(out):
    """Weighted graph with the minimum spanning tree highlighted in green."""
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 24, 40)

    rng = random.Random(7)
    weight = ogdf.EdgeArrayDouble(g)
    for e in g.edges():
        weight[e] = rng.uniform(1.0, 10.0)

    in_tree = ogdf.EdgeArrayBool(g)
    total = ogdf.min_spanning_tree(g, weight, in_tree)

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.FMMMLayout().call(ga)
    for v in g.nodes():
        ga.set_fill_color(v, ogdf.Color(70, 110, 200))
    for e in g.edges():
        if in_tree[e]:
            ga.set_edge_stroke_color(e, ogdf.Color(20, 150, 60))
            ga.set_edge_stroke_width(e, 3.0)
        else:
            ga.set_edge_stroke_color(e, ogdf.Color(210, 210, 210))
            ga.set_edge_stroke_width(e, 1.0)

    path = out / "algo_mst.svg"
    ogdf.draw_svg(ga, str(path))
    return f"minimum spanning tree (weight {total:.1f}) -> {path.name}"


def demo_steiner(out):
    """Minimum Steiner tree connecting a set of terminal nodes."""
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 30, 50)
    nodes = list(g.nodes())

    rng = random.Random(11)
    weight = ogdf.EdgeArrayDouble(g)
    for e in g.edges():
        weight[e] = rng.uniform(1.0, 10.0)
    terminals = rng.sample(nodes, 5)
    total, tree_edges = ogdf.steiner_tree(g, weight, terminals)

    tree = {e.index for e in tree_edges}
    terms = {v.index for v in terminals}

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.FMMMLayout().call(ga)
    for v in g.nodes():
        if v.index in terms:
            ga.set_fill_color(v, ogdf.Color(220, 40, 40))  # terminals in red
            ga.set_width(v, 28.0)
            ga.set_height(v, 28.0)
        else:
            ga.set_fill_color(v, ogdf.Color(200, 200, 205))
    for e in g.edges():
        if e.index in tree:
            ga.set_edge_stroke_color(e, ogdf.Color(20, 150, 60))
            ga.set_edge_stroke_width(e, 3.0)
        else:
            ga.set_edge_stroke_color(e, ogdf.Color(225, 225, 225))
            ga.set_edge_stroke_width(e, 1.0)

    path = out / "algo_steiner.svg"
    ogdf.draw_svg(ga, str(path))
    return f"Steiner tree over 5 terminals (weight {total:.1f}) -> {path.name}"


def demo_cut_vertices_bridges(out):
    """Biconnected blocks joined by bridges; cut vertices and bridges in red."""
    g = ogdf.Graph()
    blocks = []
    for _ in range(4):
        block = [g.new_node() for _ in range(5)]
        for i in range(5):
            g.new_edge(block[i], block[(i + 1) % 5])  # a cycle is biconnected
        blocks.append(block)
    for i in range(3):
        g.new_edge(blocks[i][0], blocks[i + 1][2])  # single bridge between blocks

    cut = {v.index for v in ogdf.cut_vertices(g)}
    bridge = {e.index for e in ogdf.bridges(g)}

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.FMMMLayout().call(ga)
    for v in g.nodes():
        if v.index in cut:
            ga.set_fill_color(v, ogdf.Color(220, 40, 40))
            ga.set_width(v, 26.0)
            ga.set_height(v, 26.0)
        else:
            ga.set_fill_color(v, ogdf.Color(120, 160, 220))
    for e in g.edges():
        if e.index in bridge:
            ga.set_edge_stroke_color(e, ogdf.Color(220, 40, 40))
            ga.set_edge_stroke_width(e, 3.0)
        else:
            ga.set_edge_stroke_color(e, ogdf.Color(200, 200, 205))

    path = out / "algo_cut_vertices.svg"
    ogdf.draw_svg(ga, str(path))
    return f"{len(cut)} cut vertices, {len(bridge)} bridges -> {path.name}"


def demo_matching(out):
    """Maximum-weight matching; matched edges green, matched nodes blue."""
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 24, 40)

    rng = random.Random(3)
    weight = ogdf.EdgeArrayDouble(g)
    for e in g.edges():
        weight[e] = rng.uniform(1.0, 10.0)
    matching = ogdf.EdgeArrayBool(g)
    total = ogdf.maximum_weight_matching(g, weight, matching)

    matched_nodes = set()
    for e in g.edges():
        if matching[e]:
            matched_nodes.update((e.source.index, e.target.index))

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.FMMMLayout().call(ga)
    for v in g.nodes():
        in_match = v.index in matched_nodes
        ga.set_fill_color(
            v, ogdf.Color(70, 110, 200) if in_match else ogdf.Color(210, 210, 215)
        )
    for e in g.edges():
        if matching[e]:
            ga.set_edge_stroke_color(e, ogdf.Color(20, 150, 60))
            ga.set_edge_stroke_width(e, 3.0)
        else:
            ga.set_edge_stroke_color(e, ogdf.Color(220, 220, 225))

    path = out / "algo_matching.svg"
    ogdf.draw_svg(ga, str(path))
    return f"maximum-weight matching (weight {total:.1f}) -> {path.name}"


def demo_bellman_ford(out):
    """Single-source DAG with some negative edges, shaded by distance.

    Every node is made reachable from the source so distances are well defined
    (relaxing edges out of unreachable nodes with negative weights would produce
    garbage).
    """
    g = ogdf.Graph()
    source = g.new_node()
    layers = [[source]]
    for _ in range(4):
        layers.append([g.new_node() for _ in range(4)])

    rng = random.Random(5)
    length = ogdf.EdgeArrayInt(g)
    for i in range(len(layers) - 1):
        parents = layers[i]
        for w in layers[i + 1]:
            chosen = {rng.choice(parents)}  # guarantee at least one parent
            chosen.update(u for u in parents if rng.random() < 0.4)
            for u in chosen:
                e = g.new_edge(u, w)
                length[e] = rng.randint(-2, 6)  # negative weights allowed

    dist = ogdf.NodeArrayInt(g)
    ogdf.bellman_ford(g, source, length, dist)

    values = [dist[v] for v in g.nodes()]
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.SugiyamaLayout().call(ga)
    for v in g.nodes():
        ga.set_fill_color(v, gradient_color((dist[v] - lo) / span))

    path = out / "algo_bellman_ford.svg"
    ogdf.draw_svg(ga, str(path))
    return f"Bellman-Ford distances ({lo}..{hi}) -> {path.name}"


def demo_min_cost_flow(out):
    """Single-source/sink network; edge width proportional to flow."""
    g = ogdf.Graph()
    s = g.new_node()
    t = g.new_node()
    mids = [g.new_node() for _ in range(5)]

    lower = ogdf.EdgeArrayInt(g, 0)
    upper = ogdf.EdgeArrayInt(g)
    cost = ogdf.EdgeArrayDouble(g)
    in_edges, out_edges = [], []
    for i, mid in enumerate(mids):
        e_in = g.new_edge(s, mid)
        e_out = g.new_edge(mid, t)
        upper[e_in] = 3
        upper[e_out] = 3
        cost[e_in] = float(i + 1)  # cheaper mids first
        cost[e_out] = 1.0
        in_edges.append(e_in)
        out_edges.append(e_out)

    supply = ogdf.NodeArrayInt(g)
    supply[s] = 6
    supply[t] = -6
    flow = ogdf.EdgeArrayInt(g)
    ogdf.min_cost_flow(g, lower, upper, cost, supply, flow)

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.SugiyamaLayout().call(ga)
    ga.set_fill_color(s, ogdf.Color(40, 160, 80))
    ga.set_fill_color(t, ogdf.Color(200, 60, 60))
    for mid in mids:
        ga.set_fill_color(mid, ogdf.Color(180, 190, 210))
    for e in g.edges():
        if flow[e] > 0:
            ga.set_edge_stroke_color(e, ogdf.Color(20, 120, 200))
            ga.set_edge_stroke_width(e, 1.0 + 1.5 * flow[e])
        else:
            ga.set_edge_stroke_color(e, ogdf.Color(220, 220, 225))

    total_cost = sum(flow[e] * cost[e] for e in g.edges())
    path = out / "algo_min_cost_flow.svg"
    ogdf.draw_svg(ga, str(path))
    return f"min-cost flow (cost {total_cost:.0f}) -> {path.name}"


def demo_planar_subgraph(out):
    """A non-planar graph with the edges removed to planarize it in red."""
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 22, 30)
    nodes = list(g.nodes())
    rng = random.Random(2)
    # Embedding a K5 among 5 nodes guarantees the graph is non-planar.
    clique = rng.sample(nodes, 5)
    for i in range(len(clique)):
        for j in range(i + 1, len(clique)):
            g.new_edge(clique[i], clique[j])

    removed = {e.index for e in ogdf.maximal_planar_subgraph(g)}

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.FMMMLayout().call(ga)
    for v in g.nodes():
        ga.set_fill_color(v, ogdf.Color(120, 160, 220))
    for e in g.edges():
        if e.index in removed:
            ga.set_edge_stroke_color(e, ogdf.Color(220, 40, 40))
            ga.set_edge_stroke_width(e, 2.5)
        else:
            ga.set_edge_stroke_color(e, ogdf.Color(190, 190, 195))

    path = out / "algo_planar_subgraph.svg"
    ogdf.draw_svg(ga, str(path))
    return f"maximal planar subgraph ({len(removed)} edges removed) -> {path.name}"


def demo_a_star(out):
    """Grid graph with the A* shortest path between two corners highlighted."""
    g = ogdf.Graph()
    ogdf.grid_graph(g, 8, 8)
    nodes = list(g.nodes())
    source, target = nodes[0], nodes[-1]  # opposite corners
    cost = ogdf.EdgeArrayDouble(g, 1.0)
    result = ogdf.a_star_search(g, cost, source, target)
    length, path_edges = result
    on_path_edges = {e.index for e in path_edges}
    on_path_nodes = set()
    for e in path_edges:
        on_path_nodes.update((e.source.index, e.target.index))

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.FMMMLayout().call(ga)
    for v in g.nodes():
        if v.index in {source.index, target.index}:
            ga.set_fill_color(v, ogdf.Color(220, 40, 40))  # endpoints in red
            ga.set_width(v, 26.0)
            ga.set_height(v, 26.0)
        elif v.index in on_path_nodes:
            ga.set_fill_color(v, ogdf.Color(40, 160, 80))
        else:
            ga.set_fill_color(v, ogdf.Color(200, 200, 205))
    for e in g.edges():
        if e.index in on_path_edges:
            ga.set_edge_stroke_color(e, ogdf.Color(20, 150, 60))
            ga.set_edge_stroke_width(e, 3.0)
        else:
            ga.set_edge_stroke_color(e, ogdf.Color(215, 215, 220))

    path = out / "algo_a_star.svg"
    ogdf.draw_svg(ga, str(path))
    return f"A* path length {length:.0f} ({len(on_path_edges)} edges) -> {path.name}"


def demo_min_st_cut(out):
    """s-t network with the minimum cut edges highlighted and flow-scaled."""
    g = ogdf.Graph()
    s = g.new_node()
    t = g.new_node()
    mids = [g.new_node() for _ in range(6)]

    rng = random.Random(13)
    cap = ogdf.EdgeArrayDouble(g)
    for mid in mids:
        e_in = g.new_edge(s, mid)
        e_out = g.new_edge(mid, t)
        cap[e_in] = rng.uniform(1.0, 5.0)
        cap[e_out] = rng.uniform(1.0, 5.0)
    # A couple of cross edges to make the cut non-trivial.
    cap[g.new_edge(mids[0], mids[3])] = rng.uniform(1.0, 5.0)
    cap[g.new_edge(mids[1], mids[4])] = rng.uniform(1.0, 5.0)

    flow_value = ogdf.max_flow(g, cap, s, t, ogdf.EdgeArrayDouble(g))
    cut_value, cut_edges = ogdf.min_st_cut(g, cap, s, t)
    cut = {e.index for e in cut_edges}

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.SugiyamaLayout().call(ga)
    ga.set_fill_color(s, ogdf.Color(40, 160, 80))
    ga.set_fill_color(t, ogdf.Color(200, 60, 60))
    for mid in mids:
        ga.set_fill_color(mid, ogdf.Color(180, 190, 210))
    for e in g.edges():
        if e.index in cut:
            ga.set_edge_stroke_color(e, ogdf.Color(220, 40, 40))
            ga.set_edge_stroke_width(e, 3.0)
        else:
            ga.set_edge_stroke_color(e, ogdf.Color(200, 200, 205))

    path = out / "algo_min_st_cut.svg"
    ogdf.draw_svg(ga, str(path))
    return (
        f"min s-t cut {cut_value:.1f} == max flow {flow_value:.1f} "
        f"({len(cut)} edges) -> {path.name}"
    )


def demo_crossings(out):
    """Non-planar graph drawn with a planarization layout; count its crossings."""
    g = ogdf.Graph()
    ogdf.complete_graph(g, 6)  # K6 is non-planar (crossing number 3)

    cr = ogdf.crossing_number(g)
    # Route the non-subgraph edges back in and highlight the ones that cross.
    removed = ogdf.maximal_planar_subgraph(g)
    routes = ogdf.insert_edges(g, list(removed))
    crossed = {c.index for _, edges in routes for c in edges}
    inserted = {e.index for e, _ in routes}

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.PlanarizationLayout().call(ga)
    for v in g.nodes():
        ga.set_fill_color(v, ogdf.Color(120, 160, 220))
    for e in g.edges():
        if e.index in inserted:
            ga.set_edge_stroke_color(e, ogdf.Color(220, 40, 40))  # re-inserted
            ga.set_edge_stroke_width(e, 2.5)
        elif e.index in crossed:
            ga.set_edge_stroke_color(e, ogdf.Color(230, 150, 30))  # gets crossed
            ga.set_edge_stroke_width(e, 2.0)
        else:
            ga.set_edge_stroke_color(e, ogdf.Color(190, 190, 195))

    path = out / "algo_crossings.svg"
    ogdf.draw_svg(ga, str(path))
    return f"K6 crossing number {cr}, {len(inserted)} edges reinserted -> {path.name}"


def demo_connectivity(out):
    """Blocks of increasing connectivity, colored by their edge connectivity."""
    g = ogdf.Graph()
    # Three components: a path (1), a cycle (2), and K4 (3).
    a = [g.new_node() for _ in range(4)]
    for i in range(3):
        g.new_edge(a[i], a[i + 1])  # path -> edge connectivity 1
    b = [g.new_node() for _ in range(5)]
    for i in range(5):
        g.new_edge(b[i], b[(i + 1) % 5])  # cycle -> edge connectivity 2
    c = [g.new_node() for _ in range(4)]
    for i in range(4):
        for j in range(i + 1, 4):
            g.new_edge(c[i], c[j])  # K4 -> edge connectivity 3

    # Compute each block's connectivity on its own subgraph.
    labels = []
    for block in (a, b, c):
        h = ogdf.Graph()
        idx = {v.index: h.new_node() for v in block}
        block_idx = {v.index for v in block}
        for e in g.edges():
            if e.source.index in block_idx and e.target.index in block_idx:
                h.new_edge(idx[e.source.index], idx[e.target.index])
        labels.append((block, ogdf.edge_connectivity(h), ogdf.node_connectivity(h)))

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.FMMMLayout().call(ga)
    ramp = {
        1: ogdf.Color(120, 170, 230),
        2: ogdf.Color(90, 190, 120),
        3: ogdf.Color(230, 150, 40),
    }
    for block, ec, _ in labels:
        for v in block:
            ga.set_fill_color(v, ramp.get(ec, ogdf.Color(200, 200, 205)))

    path = out / "algo_connectivity.svg"
    ogdf.draw_svg(ga, str(path))
    summary = ", ".join(f"{k}-edge/{n}-node" for _, k, n in labels)
    return f"edge/node connectivity per block ({summary}) -> {path.name}"


def demo_strong_components(out):
    """Directed cycles chained feed-forward, colored by strong component."""
    g = ogdf.Graph()
    # Four directed cycles (each a strongly connected component) linked in a
    # one-way chain, so the SCCs are distinct and the condensation is a DAG.
    cycles = []
    for _ in range(4):
        ring = [g.new_node() for _ in range(4)]
        for i in range(4):
            g.new_edge(ring[i], ring[(i + 1) % 4])  # directed cycle
        cycles.append(ring)
    for i in range(3):
        g.new_edge(cycles[i][0], cycles[i + 1][0])  # one-way link between rings

    comp = ogdf.NodeArrayInt(g)
    k = ogdf.strong_components(g, comp)

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.FMMMLayout().call(ga)
    colors = palette(k)
    for v in g.nodes():
        ga.set_fill_color(v, colors[comp[v]])
    for e in g.edges():
        ga.set_arrow(e, ogdf.EdgeArrow.LAST)

    path = out / "algo_strong_components.svg"
    ogdf.draw_svg(ga, str(path))
    return f"{k} strongly connected components -> {path.name}"


def demo_biconnected_components(out):
    """Blocks joined at cut vertices, edges colored by biconnected component."""
    g = ogdf.Graph()
    blocks = []
    for _ in range(4):
        block = [g.new_node() for _ in range(5)]
        for i in range(5):
            g.new_edge(block[i], block[(i + 1) % 5])  # a cycle is one block
        blocks.append(block)
    for i in range(3):
        g.new_edge(blocks[i][0], blocks[i + 1][2])  # bridges are their own block

    comp = ogdf.EdgeArrayInt(g)
    k = ogdf.biconnected_components(g, comp)

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.FMMMLayout().call(ga)
    colors = palette(k)
    for v in g.nodes():
        ga.set_fill_color(v, ogdf.Color(210, 210, 215))
    for e in g.edges():
        ga.set_edge_stroke_color(e, colors[comp[e]])
        ga.set_edge_stroke_width(e, 2.5)

    path = out / "algo_biconnected.svg"
    ogdf.draw_svg(ga, str(path))
    return f"{k} biconnected components -> {path.name}"


def demo_topological_numbering(out):
    """A DAG laid out hierarchically and shaded by topological order."""
    g = ogdf.Graph()
    ogdf.random_series_parallel_dag(g, 24)

    num = ogdf.NodeArrayInt(g)
    ogdf.topological_numbering(g, num)
    hi = max((num[v] for v in g.nodes()), default=1) or 1

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.SugiyamaLayout().call(ga)
    for v in g.nodes():
        ga.set_fill_color(v, gradient_color(num[v] / hi))
    for e in g.edges():
        ga.set_arrow(e, ogdf.EdgeArrow.LAST)

    path = out / "algo_topological.svg"
    ogdf.draw_svg(ga, str(path))
    return f"topological numbering (0..{hi}) -> {path.name}"


def demo_triconnectivity(out):
    """Two triconnected blocks sharing a separation pair (highlighted red)."""
    g = ogdf.Graph()
    u, v = g.new_node(), g.new_node()  # the shared separation pair
    blocks = []
    for _ in range(2):
        w1, w2 = g.new_node(), g.new_node()
        block = [u, v, w1, w2]
        for i in range(4):  # K4 on {u, v, w1, w2} -> a rigid (triconnected) block
            for j in range(i + 1, 4):
                if not (block[i] in (u, v) and block[j] in (u, v)):
                    g.new_edge(block[i], block[j])
        blocks.append((w1, w2))
    g.new_edge(u, v)  # the single shared edge

    pair = ogdf.separation_pair(g)
    summary = ogdf.spqr_tree_summary(g)
    pair_idx = {pair[0].index, pair[1].index} if pair else set()

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.FMMMLayout().call(ga)
    block_colors = [ogdf.Color(120, 170, 230), ogdf.Color(90, 190, 120)]
    for i, (w1, w2) in enumerate(blocks):
        ga.set_fill_color(w1, block_colors[i])
        ga.set_fill_color(w2, block_colors[i])
    for w in (u, v):
        ga.set_fill_color(w, ogdf.Color(220, 40, 40))  # separation pair in red
        ga.set_width(w, 26.0)
        ga.set_height(w, 26.0)

    path = out / "algo_triconnectivity.svg"
    ogdf.draw_svg(ga, str(path))
    return (
        f"separation pair {sorted(pair_idx)}, SPQR R={summary['R']} "
        f"S={summary['S']} P={summary['P']} -> {path.name}"
    )


def main():
    out = output_dir()
    print("Algorithm visualizations:")
    for demo in (
        demo_components,
        demo_strong_components,
        demo_biconnected_components,
        demo_coloring,
        demo_shortest_paths,
        demo_a_star,
        demo_bellman_ford,
        demo_topological_numbering,
        demo_mst,
        demo_min_cost_flow,
        demo_min_st_cut,
        demo_cut_vertices_bridges,
        demo_connectivity,
        demo_triconnectivity,
        demo_matching,
        demo_steiner,
        demo_planar_subgraph,
        demo_crossings,
    ):
        print(f"  {demo(out)}")


if __name__ == "__main__":
    main()
