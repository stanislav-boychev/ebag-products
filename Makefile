.PHONY: install db db-stop db-reset psql migrate migration run test lint fmt

# Create .venv and install dependencies
install:
	uv sync

# Start Postgres and wait until it accepts connections
db:
	docker compose up -d --wait

# Stop Postgres, keeping the data
db-stop:
	docker compose down

# Delete all data and start an empty database
db-reset:
	docker compose down -v
	docker compose up -d --wait

# SQL shell into the database
psql:
	docker compose exec postgres psql -U ebag -d products

# Apply all migrations
migrate:
	uv run alembic upgrade head

# New migration from model changes: make migration m="add stock"
migration:
	uv run alembic revision --autogenerate -m "$(m)"

# API on http://localhost:8000, docs on /docs
run:
	uv run uvicorn app.main:app --reload --port 8000

# All tests, in a separate products_test database
test:
	uv run pytest -v

# Check style and likely bugs without changing anything
lint:
	uv run ruff check .
	uv run ruff format --check .

# Sort imports, fix what can be fixed, format the code
fmt:
	uv run ruff check --fix --exit-zero .
	uv run ruff format .
