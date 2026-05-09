.PHONY: help install dev test lint format clean docker-up docker-down run-dev

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	pip install -r requirements.txt

dev: ## Install development dependencies and set up environment
	@echo "Setting up development environment..."
	pip install --upgrade pip setuptools wheel
	pip install -r requirements.txt
	@echo "Installing pre-commit hooks..."
	pre-commit install || echo "pre-commit hooks installation skipped"
	@echo "Development environment ready!"
	
test: ## Run core service tests only
	ENVIRONMENT=development SECRET_KEY=test-key pytest tests/test_services/ -v --tb=short

test-all: ## Run all tests (many will fail - for development reference)
	ENVIRONMENT=development SECRET_KEY=test-key pytest tests/ -v --tb=short

lint: ## Run linting
	@echo "Checking code style..."
	@python -m flake8 app/ tests/ --extend-ignore=E501,W503,E203 || true
	@echo "Checking type hints..."
	@python -m mypy app/ --ignore-missing-imports || true

format: ## Format code
	@echo "Formatting code..."
	@python -m black app/ tests/ --quiet || true
	@python -m isort app/ tests/ --quiet || true
	@echo "Code formatting completed"

clean: ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/

docker-up: ## Start services with Docker Compose
	docker-compose up -d

docker-down: ## Stop services with Docker Compose  
	docker-compose down

run-dev: ## Run development server
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

db-migrate: ## Run database migrations
	alembic upgrade head

db-revision: ## Create new database revision
	alembic revision --autogenerate -m "$(msg)"

test-coverage: ## Run tests with coverage report
	pytest tests/ -v --cov=app --cov-report=term-missing

security-check: ## Run security checks
	bandit -r app/
	safety check
