import random
import socket
import threading

from config_loader import load_routers_config, load_links_config
from graph import build_graph, build_forwarding_table, shortest_path
from logger import get_logger
from packet import deserialize, make_ack, make_data, serialize
from reliability import StopAndWait

LOSS_PROBABILITY = 0.10


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

        next_hop = self.forwarding_table.get(destination)
        if next_hop is None:
            print(f"Nao ha proximo salto para o destino {destination}.")
            return

        self.seq += 1
        seq = self.seq
        packet = make_data(seq, self.id, destination, payload, path)

        self.saw.set_pending(seq)
        attempt = 0

        while True:
            attempt += 1
            if attempt == 1:
                self.logger.info('[ENVIADA]      Seq %s destino %s payload="%s"', seq, destination, payload)
                print(
                    f"Roteador {self.id} encaminhando mensagem (Seq: {seq}) "
                    f"para o destino {destination} via proximo salto {next_hop}"
                )
            else:
                self.logger.info("[REENVIO]      Seq %s destino %s tentativa %s", seq, destination, attempt)
                print(f"Roteador {self.id} timeout (Seq: {seq}) — reenviando tentativa {attempt}")

            self.send_packet(next_hop, packet)

            if self.saw.wait_for_ack(timeout=3):
                self.logger.info("[ACK_RECEBIDO] Seq %s de destino %s", seq, destination)
                print(f"Roteador {self.id} recebeu ACK (Seq: {seq}) — mensagem entregue com sucesso")
                break

    def handle_packet(self, packet):
        ptype = packet.get("type")
        seq = packet.get("seq")
        origin = packet.get("origin")
        dest = packet.get("destination")

        if random.random() < LOSS_PROBABILITY:
            self.logger.info(
                "[DESCARTE]     %s Seq %s origem %s destino %s",
                ptype, seq, origin, dest,
            )
            print(f"Roteador {self.id} descartou pacote {ptype} (Seq: {seq}) — perda simulada")
            return

        if ptype == "DATA":
            self._handle_data(packet)
        elif ptype == "ACK":
            self._handle_ack(packet)
        else:
            print(f"Roteador {self.id} recebeu pacote desconhecido tipo '{ptype}'")

    def _handle_data(self, packet):
        destination = packet["destination"]

        if destination == self.id:
            self._deliver_packet(packet)
            return

        next_hop = self.forwarding_table.get(destination)
        if next_hop is None:
            print(
                f"Roteador {self.id} nao possui rota para {destination}; "
                f"DATA Seq {packet['seq']} descartado."
            )
            return

        self.send_packet(next_hop, packet)
        self.logger.info(
            "[ENCAMINHADA]  Seq %s origem %s destino %s proximo_salto %s",
            packet["seq"], packet["origin"], destination, next_hop,
        )
        print(
            f"Roteador {self.id} encaminhando mensagem (Seq: {packet['seq']}) "
            f"para o destino {destination} via proximo salto {next_hop}"
        )

    def _handle_ack(self, packet):
        destination = packet["destination"]  # original DATA sender

        if destination == self.id:
            # Unblocks saw.wait_for_ack() in send_message()
            self.saw.on_ack(packet["seq"])
            return

        next_hop = self.forwarding_table.get(destination)
        if next_hop is None:
            print(f"Roteador {self.id} nao possui rota para ACK destino {destination}.")
            return

        self.send_packet(next_hop, packet)

    def _deliver_packet(self, packet):
        origin = packet["origin"]
        seq = packet["seq"]
        payload = packet["payload"]

        # Deduplication: duplicate DATA means the previous ACK was lost; resend ACK only
        if self.last_received_seq.get(origin) == seq:
            self._send_ack(seq, origin)
            return

        self.last_received_seq[origin] = seq
        self.logger.info('[RECEBIDA]     Seq %s origem %s payload="%s"', seq, origin, payload)
        print(f'Roteador {self.id} recebeu mensagem (Seq: {seq}) de {origin}: "{payload}"')

        self._send_ack(seq, origin)

    def _send_ack(self, seq, origin):
        ack_next_hop = self.forwarding_table.get(origin)
        if ack_next_hop is None:
            print(f"Roteador {self.id} nao possui rota de volta para {origin}; ACK nao enviado.")
            return

        ack = make_ack(seq, self.id, origin)
        self.send_packet(ack_next_hop, ack)
        self.logger.info("[ACK_ENVIADO]  Seq %s para origem %s", seq, origin)
        print(f"Roteador {self.id} enviou ACK (Seq: {seq}) para {origin} via proximo salto {ack_next_hop}")

    def send_packet(self, next_hop, packet):
        router_info = self.routers[next_hop]
        self.sock.sendto(serialize(packet), (router_info["ip"], router_info["port"]))

    def stop(self):
        self.running = False
        self.sock.close()
