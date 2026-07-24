COMPOSE ?= docker compose

.PHONY: up down reset logs

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

reset:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f
