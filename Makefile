COMPOSE ?= docker compose

.PHONY: up down reset logs verify-phase0 test-backend-auth test-backend export-openapi verify-openapi

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

reset:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f

verify-phase0:
	$(COMPOSE) config >/dev/null
	@echo "[verify] compose config is valid"
	$(COMPOSE) ps
	@curl -fsS http://localhost:5173 >/dev/null
	@echo "[verify] frontend reachable at http://localhost:5173"
	@curl -fsS http://localhost:8000/api/health >/dev/null
	@echo "[verify] backend health endpoint is reachable"
	@curl -fsS http://localhost:5678/healthz >/dev/null
	@echo "[verify] n8n health endpoint is reachable"
	$(COMPOSE) exec -T postgres pg_isready -U postgres -d contracts
	@echo "[verify] postgres is ready"
	$(COMPOSE) exec -T redis redis-cli ping | grep -q PONG
	@echo "[verify] redis ping succeeded"
	$(COMPOSE) exec -T celery-worker celery -A app.celery_app:celery_app inspect ping
	@echo "[verify] celery worker responds to inspect ping"

test-backend-auth:
	@if cd apps/backend && python3 -c "import fastapi" >/dev/null 2>&1; then \
		cd apps/backend && python3 -m unittest -v tests/test_internal_api_auth.py; \
	else \
		$(COMPOSE) run --rm backend python -m unittest -v tests/test_internal_api_auth.py; \
	fi

test-backend:
	@if cd apps/backend && python3 -c "import fastapi" >/dev/null 2>&1; then \
		cd apps/backend && python3 -m unittest discover -v -s tests; \
	else \
		$(COMPOSE) run --rm backend python -m unittest discover -v -s tests; \
	fi

export-openapi:
	@if cd apps/backend && python3 -c "import fastapi" >/dev/null 2>&1; then \
		cd apps/backend && python3 scripts/export_openapi.py; \
	else \
		$(COMPOSE) run --rm backend python scripts/export_openapi.py; \
	fi

verify-openapi:
	@if cd apps/backend && python3 -c "import fastapi" >/dev/null 2>&1; then \
		cd apps/backend && python3 scripts/check_openapi_drift.py; \
	else \
		$(COMPOSE) run --rm backend python scripts/check_openapi_drift.py; \
	fi
