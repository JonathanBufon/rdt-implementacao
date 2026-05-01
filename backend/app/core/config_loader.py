from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RouterConfig:
    id: int
    port: int
    ip: str


@dataclass(frozen=True)
class LinkConfig:
    source: int
    target: int
    cost: int


@dataclass(frozen=True)
class TopologyConfig:
    routers: list[RouterConfig]
    links: list[LinkConfig]
    adjacency: dict[int, dict[int, int]]

    def to_api_response(self) -> dict[str, list[dict[str, int | str]]]:
        return {
            "routers": [
                {"id": router.id, "ip": router.ip, "port": router.port}
                for router in sorted(self.routers, key=lambda router: router.id)
            ],
            "links": [
                {"source": link.source, "target": link.target, "cost": link.cost}
                for link in self.links
            ],
        }


def load_topology(config_dir: Path) -> TopologyConfig:
    routers = load_routers(config_dir / "roteador.config")
    links = load_links(config_dir / "enlaces.config")
    adjacency = build_adjacency(routers, links)
    return TopologyConfig(routers=routers, links=links, adjacency=adjacency)


def load_routers(path: Path) -> list[RouterConfig]:
    routers: list[RouterConfig] = []
    seen_ids: set[int] = set()

    for line_number, line in _iter_config_lines(path):
        parts = line.split()
        if len(parts) != 3:
            raise ValueError(f"{path}:{line_number}: expected '[ID] [Porta] [IP]'")

        router_id = _parse_positive_int(parts[0], path, line_number, "ID")
        port = _parse_positive_int(parts[1], path, line_number, "Porta")
        ip = parts[2]

        if router_id in seen_ids:
            raise ValueError(f"{path}:{line_number}: duplicated router ID {router_id}")

        seen_ids.add(router_id)
        routers.append(RouterConfig(id=router_id, port=port, ip=ip))

    if not routers:
        raise ValueError(f"{path}: no routers configured")

    return routers


def load_links(path: Path) -> list[LinkConfig]:
    links: list[LinkConfig] = []

    for line_number, line in _iter_config_lines(path):
        parts = line.split()
        if len(parts) != 3:
            raise ValueError(f"{path}:{line_number}: expected '[ID_Origem] [ID_Destino] [Custo]'")

        source = _parse_positive_int(parts[0], path, line_number, "ID_Origem")
        target = _parse_positive_int(parts[1], path, line_number, "ID_Destino")
        cost = _parse_positive_int(parts[2], path, line_number, "Custo")

        if source == target:
            raise ValueError(f"{path}:{line_number}: source and target must be different")

        links.append(LinkConfig(source=source, target=target, cost=cost))

    if not links:
        raise ValueError(f"{path}: no links configured")

    return links


def build_adjacency(
    routers: list[RouterConfig],
    links: list[LinkConfig],
) -> dict[int, dict[int, int]]:
    router_ids = {router.id for router in routers}
    adjacency: dict[int, dict[int, int]] = {router_id: {} for router_id in router_ids}

    for link in links:
        if link.source not in router_ids:
            raise ValueError(f"link source router {link.source} is not configured")
        if link.target not in router_ids:
            raise ValueError(f"link target router {link.target} is not configured")

        adjacency[link.source][link.target] = link.cost
        adjacency[link.target][link.source] = link.cost

    return adjacency


def _iter_config_lines(path: Path) -> list[tuple[int, str]]:
    if not path.exists():
        raise ValueError(f"{path}: file not found")

    lines: list[tuple[int, str]] = []
    with path.open(encoding="utf-8") as config_file:
        for line_number, raw_line in enumerate(config_file, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            lines.append((line_number, line))

    return lines


def _parse_positive_int(value: str, path: Path, line_number: int, field: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{path}:{line_number}: {field} must be an integer") from exc

    if parsed <= 0:
        raise ValueError(f"{path}:{line_number}: {field} must be positive")

    return parsed
