import heapq


def build_graph(links):
    graph = {}
    for a, b, cost in links:
        graph.setdefault(a, []).append((b, cost))
        graph.setdefault(b, []).append((a, cost))
    return graph


def _dijkstra(graph, source):
    dist = {source: 0}
    prev = {}
    heap = [(0, source)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist.get(u, float("inf")):
            continue
        for v, w in graph.get(u, []):
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(heap, (nd, v))
    return dist, prev


def shortest_path(graph, source, destination):
    _, prev = _dijkstra(graph, source)
    if destination not in prev and destination != source:
        return []
    path = []
    node = destination
    while node in prev:
        path.append(node)
        node = prev[node]
    path.append(source)
    path.reverse()
    return path


def build_forwarding_table(graph, source):
    _, prev = _dijkstra(graph, source)
    table = {}
    for dest in graph:
        if dest == source or dest not in prev:
            continue
        node = dest
        while prev.get(node) != source:
            node = prev[node]
        table[dest] = node
    return table
