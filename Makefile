.PHONY: dev-deps migrate backend frontend test down

# Start dev Postgres (and pgAdmin) in the background
dev-deps:
	docker compose up -d

# Run Alembic migrations against the dev database
migrate:
	cd backend && uv run alembic upgrade head

# Start the FastAPI dev server (port 8000)
backend:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

# Start the Vite dev server (port 5173)
frontend:
	cd frontend && npm run dev

# Spin up the test DB, run all tests, then tear it down
test:
	docker compose -f docker-compose.test.yml up -d --wait
	cd backend && uv run pytest $(PYTEST_ARGS)
	cd frontend && npm run test -- --run
	docker compose -f docker-compose.test.yml down

# Stop and remove all dev containers
down:
	docker compose down
