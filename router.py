import socket
import threading

from config_loader import load_routers_config, load_links_config
from graph import build_graph, build_forwarding_table, shortest_path
from logger import get_logger
from packet import deserialize, make_data, serialize
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
        self.running = False
        self.listener_thread = None

    def start(self):
        self.running = True
        self.listener_thread = threading.Thread(target=self.listen, daemon=True)
        self.listener_thread.start()

    def listen(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(4096)
                packet = deserialize(data)
                self.handle_packet(packet)
            except OSError:
                break
            except Exception as exc:
                print(f"Roteador {self.id} erro ao receber pacote: {exc}")

    def command_loop(self):
        while self.running:
            try:
                command = input()
            except (EOFError, KeyboardInterrupt):
                self.stop()
                break

            if not command.strip():
                continue
            if command.strip().lower() in {"exit", "quit"}:
                self.stop()
                break
            self.handle_command(command)

    def handle_command(self, command):
        parts = command.strip().split(maxsplit=2)
        if len(parts) < 3 or parts[0] != "send":
            print("Uso: send <destino> <mensagem>")
            return

        try:
            destination = int(parts[1])
        except ValueError:
            print("Destino deve ser um numero inteiro.")
            return

        payload = parts[2]
        if len(payload) > 100:
            print("Mensagem rejeitada: payload deve ter no maximo 100 caracteres.")
            return

        self.send_message(destination, payload)

    def send_message(self, destination, payload):
        if destination == self.id:
            print("Destino deve ser diferente do roteador atual.")
            return
        if destination not in self.routers:
            print(f"Destino {destination} nao encontrado em roteador.config.")
            return

        path = shortest_path(self.graph, self.id, destination)
        if not path:
            print(f"Nao ha rota do roteador {self.id} para o destino {destination}.")
            return

        self.seq += 1
        packet = make_data(self.seq, self.id, destination, payload, path)
        next_hop = self.forwarding_table.get(destination)
        if next_hop is None:
            print(f"Nao ha proximo salto para o destino {destination}.")
            return

        self.send_packet(next_hop, packet)
        self.logger.info(
            '[ENVIADA]      Seq %s destino %s payload="%s"',
            packet["seq"],
            destination,
            payload,
        )
        print(
            f"Roteador {self.id} encaminhando mensagem (Seq: {packet['seq']}) "
            f"para o destino {destination} via proximo salto {next_hop}"
        )

    def handle_packet(self, packet):
        if packet.get("type") != "DATA":
            print(f"Roteador {self.id} recebeu pacote desconhecido: {packet}")
            return

        destination = packet["destination"]
        if destination == self.id:
            self.deliver_packet(packet)
            return

        next_hop = self.forwarding_table.get(destination)
        if next_hop is None:
            print(
                f"Roteador {self.id} nao possui rota para o destino {destination}; "
                f"pacote Seq {packet['seq']} descartado."
            )
            return

        self.send_packet(next_hop, packet)
        self.logger.info(
            "[ENCAMINHADA]  Seq %s origem %s destino %s proximo_salto %s",
            packet["seq"],
            packet["origin"],
            destination,
            next_hop,
        )
        print(
            f"Roteador {self.id} encaminhou mensagem (Seq: {packet['seq']}) "
            f"de {packet['origin']} para {destination} via proximo salto {next_hop}"
        )

    def deliver_packet(self, packet):
        origin = packet["origin"]
        seq = packet["seq"]
        payload = packet["payload"]
        self.last_received_seq[origin] = seq
        self.logger.info(
            '[RECEBIDA]     Seq %s origem %s payload="%s"',
            seq,
            origin,
            payload,
        )
        print(f'Roteador {self.id} recebeu mensagem (Seq: {seq}) de {origin}: "{payload}"')

    def send_packet(self, next_hop, packet):
        router_info = self.routers[next_hop]
        self.sock.sendto(serialize(packet), (router_info["ip"], router_info["port"]))

    def stop(self):
        self.running = False
        self.sock.close()
