import sys
import time

from router import Router


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 main.py <id_roteador>")
        sys.exit(1)

    router_id = int(sys.argv[1])
    router = Router(router_id)
    print(f"Roteador {router_id} iniciado em {router.ip}:{router.port}")
    router.start()
    router.command_loop()

    # Mantém o processo vivo se o roteador ainda está rodando (stdin encerrado, mas listener ativo)
    try:
        while router.running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        router.stop()


if __name__ == "__main__":
    main()
