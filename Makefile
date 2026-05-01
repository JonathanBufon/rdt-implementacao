.PHONY: up down logs backend-shell frontend-shell

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

backend-shell:
	docker compose exec backend sh

frontend-shell:
	docker compose exec frontend sh
