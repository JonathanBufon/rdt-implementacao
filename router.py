import socket

from config_loader import load_routers_config, load_links_config
from graph import build_graph, build_forwarding_table
from logger import get_logger
from reliability import StopAndWait


class Router:
    def __init__(self, router_id):
        self.id = router_id
        self.routers = load_routers_config()
        self.links = load_links_config()
        self.graph = build_graph(self.links)
        self.forwarding_table = build_forwarding_table(self.graph, router_id)
        self.logger = get_logger(router_id)
        self.saw = StopAndWait()
        self.seq = 0
        self.last_received_seq = {}  # origin_id -> last seq delivered

        info = self.routers[router_id]
        self.ip = info["ip"]
        self.port = info["port"]
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.ip, self.port))
