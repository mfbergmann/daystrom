.PHONY: help install dev run migrate migrate-create test clean docker-up docker-down

help:
	@echo "Daystrom - Available commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make dev          - Set up development environment"
	@echo "  make run          - Run the application"
	@echo "  make migrate      - Run database migrations"
	@echo "  make migrate-create MSG='description' - Create new migration"
	@echo "  make test         - Run connection tests"
	@echo "  make clean        - Clean up temporary files"
	@echo "  make docker-up    - Start Docker services (PostgreSQL)"
	@echo "  make docker-down  - Stop Docker services"

install:
	pip install --upgrade pip
	pip install -r requirements.txt

dev:
	bash scripts/setup_dev.sh

run:
	python main.py

migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(MSG)"

test:
	python scripts/test_connection.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

docker-up:
	docker-compose up -d
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 5
	@echo "PostgreSQL is ready!"

docker-down:
	docker-compose down

docker-clean:
	docker-compose down -v

