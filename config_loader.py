def load_routers_config(path="roteador.config"):
    routers = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            router_id, port, ip = int(parts[0]), int(parts[1]), parts[2]
            routers[router_id] = {"ip": ip, "port": port}
    return routers


def load_links_config(path="enlaces.config"):
    links = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            a, b, cost = int(parts[0]), int(parts[1]), int(parts[2])
            links.append((a, b, cost))
    return links
