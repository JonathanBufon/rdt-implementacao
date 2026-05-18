SESSION = rdt
LOG_DIR = logs
PORTS   = 25001 25002 25003 25004 25005

.PHONY: help start attach stop logs clean test status

# ─── Ajuda ────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "Alvos disponíveis:"
	@echo ""
	@echo "  make start   — sobe os 5 roteadores (tmux ou gnome-terminal)"
	@echo "  make attach  — reconecta à sessão tmux existente"
	@echo "  make stop    — mata todos os processos e libera as portas"
	@echo "  make logs    — exibe todos os arquivos de log"
	@echo "  make clean   — remove logs e __pycache__"
	@echo "  make test    — teste automático R1→R5 (sem abrir terminais)"
	@echo "  make status  — mostra quais roteadores estão ativos"
	@echo ""

# ─── Subir roteadores ─────────────────────────────────────────────────────────

start:
	@if command -v tmux >/dev/null 2>&1; then \
		$(MAKE) --no-print-directory _start_tmux; \
	else \
		$(MAKE) --no-print-directory _start_gnome; \
	fi

_start_tmux:
	@if tmux has-session -t $(SESSION) 2>/dev/null; then \
		echo "Sessão '$(SESSION)' já existe. Use 'make attach' ou 'make stop' primeiro."; \
	else \
		tmux new-session -d -s $(SESSION); \
		tmux send-keys -t $(SESSION) "python3 main.py 1" Enter; \
		tmux split-window -h -t $(SESSION); \
		tmux send-keys -t $(SESSION) "python3 main.py 2" Enter; \
		tmux split-window -h -t $(SESSION); \
		tmux send-keys -t $(SESSION) "python3 main.py 3" Enter; \
		tmux split-window -h -t $(SESSION); \
		tmux send-keys -t $(SESSION) "python3 main.py 4" Enter; \
		tmux split-window -h -t $(SESSION); \
		tmux send-keys -t $(SESSION) "python3 main.py 5" Enter; \
		tmux select-layout -t $(SESSION) tiled; \
		tmux attach -t $(SESSION); \
	fi

_start_gnome:
	@echo "tmux não encontrado — abrindo abas no gnome-terminal."
	@echo "  (Instale tmux para uma experiência melhor: sudo apt install tmux)"
	@gnome-terminal \
		--tab --title="R1" -- bash -c "python3 main.py 1; exec bash" \
		--tab --title="R2" -- bash -c "python3 main.py 2; exec bash" \
		--tab --title="R3" -- bash -c "python3 main.py 3; exec bash" \
		--tab --title="R4" -- bash -c "python3 main.py 4; exec bash" \
		--tab --title="R5" -- bash -c "python3 main.py 5; exec bash" \
		2>/dev/null &

attach:
	@tmux attach -t $(SESSION) 2>/dev/null \
		|| echo "Nenhuma sessão '$(SESSION)' ativa. Use 'make start'."

# ─── Parar roteadores ─────────────────────────────────────────────────────────

stop:
	@fuser -k 25001/udp 25002/udp 25003/udp 25004/udp 25005/udp 2>/dev/null || true
	@tmux kill-session -t $(SESSION) 2>/dev/null || true
	@echo "Roteadores encerrados e portas liberadas."

# ─── Logs ─────────────────────────────────────────────────────────────────────

logs:
	@for i in 1 2 3 4 5; do \
		file=$(LOG_DIR)/router_$$i.log; \
		echo "=== $$file ==="; \
		if [ -f $$file ] && [ -s $$file ]; then cat $$file; else echo "(sem eventos)"; fi; \
		echo ""; \
	done

# ─── Limpeza ──────────────────────────────────────────────────────────────────

clean:
	@rm -f $(LOG_DIR)/router_*.log
	@find . -path ./.venv -prune -o -name "__pycache__" -type d -print0 | xargs -0 rm -rf 2>/dev/null || true
	@find . -path ./.venv -prune -o -name "*.pyc" -print0 | xargs -0 rm -f 2>/dev/null || true
	@echo "Logs e cache removidos."

# ─── Status ───────────────────────────────────────────────────────────────────

status:
	@echo ""
	@printf "%-10s %-8s %s\n" "Roteador" "Porta" "Status"
	@printf "%-10s %-8s %s\n" "--------" "-----" "------"
	@n=1; for port in $(PORTS); do \
		pid=$$(fuser $$port/udp 2>/dev/null | tr -d ' '); \
		if [ -n "$$pid" ]; then \
			printf "R%-9s %-8s \033[32mATIVO\033[0m (PID $$pid)\n" $$n $$port; \
		else \
			printf "R%-9s %-8s \033[90mlivre\033[0m\n" $$n $$port; \
		fi; \
		n=$$((n+1)); \
	done
	@echo ""

# ─── Teste automático ─────────────────────────────────────────────────────────

test:
	@echo "==> Limpando estado anterior..."
	@fuser -k 25001/udp 25002/udp 25003/udp 25004/udp 25005/udp 2>/dev/null; \
	 rm -f $(LOG_DIR)/router_*.log /tmp/r1.log /tmp/r2.log /tmp/r3.log /tmp/r4.log /tmp/r5.log; \
	 sleep 0.5; \
	 echo "==> Iniciando roteadores 2–5 em background..."; \
	 for i in 2 3 4 5; do \
	   PYTHONUNBUFFERED=1 python3 main.py $$i </dev/null >/tmp/r$$i.log 2>&1 & \
	 done; \
	 sleep 1; \
	 echo "==> Enviando: R1 → R5 \"Ola roteador 5\""; \
	 { echo "send 5 Ola roteador 5"; sleep 15; } \
	   | PYTHONUNBUFFERED=1 python3 main.py 1 >/tmp/r1.log 2>&1; \
	 fuser -k 25001/udp 25002/udp 25003/udp 25004/udp 25005/udp 2>/dev/null; true
	@echo ""
	@echo "──── Console R1 (origem) ────────────────────────"
	@cat /tmp/r1.log
	@echo ""
	@echo "──── Console R3 (intermediário) ─────────────────"
	@cat /tmp/r3.log
	@echo ""
	@echo "──── Console R5 (destino) ───────────────────────"
	@cat /tmp/r5.log
	@echo ""
	@echo "──── Logs de arquivo ────────────────────────────"
	@$(MAKE) --no-print-directory logs
