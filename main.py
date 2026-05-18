import sys

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


if __name__ == "__main__":
    main()
