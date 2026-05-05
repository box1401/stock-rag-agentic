.PHONY: dev down logs api web db migrate fmt lint test smoke

dev:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

api:
	docker compose up -d db && cd apps/api && uvicorn app.main:app --reload --port 8000

web:
	cd apps/web && npm run dev

db:
	docker compose up -d db

migrate:
	cd apps/api && alembic upgrade head

revision:
	cd apps/api && alembic revision --autogenerate -m "$(m)"

fmt:
	cd apps/api && ruff format . && ruff check --fix .
	cd apps/web && npm run format

lint:
	cd apps/api && ruff check . && mypy app
	cd apps/web && npm run lint

test:
	cd apps/api && pytest -v --cov=app --cov-report=term-missing

smoke:
	curl -s http://localhost:8000/health | jq .
	curl -s -X POST http://localhost:8000/api/v1/analyze \
	  -H "Content-Type: application/json" \
	  -d '{"ticker":"2330","mode":"daily"}' | jq .
