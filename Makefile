# Somali NLP Data Pipeline - Development Makefile
# Quick commands for common development tasks

.PHONY: help dev dev-all docker-build docker-up docker-down docker-logs test lint clean

# Default target
help:
	@echo "Somali NLP Pipeline - Development Commands"
	@echo ""
	@echo "Local Development (SQLite):"
	@echo "  make dev PIPELINE=wikipedia    Run specific pipeline locally"
	@echo "  make dev PIPELINE=bbc ARGS='--max-bbc-articles 100'"
	@echo "  make dev-all                   Run all pipelines locally"
	@echo ""
	@echo "Docker (PostgreSQL):"
	@echo "  make docker-build              Build Docker images"
	@echo "  make docker-up                 Start production stack"
	@echo "  make docker-down               Stop all containers"
	@echo "  make docker-logs               View container logs"
	@echo "  make docker-test               Run pipeline in Docker"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test                      Run all tests"
	@echo "  make test-security             Run security tests"
	@echo "  make lint                      Run code quality checks"
	@echo "  make secrets-check             Scan for secrets (fast - staged files only)"
	@echo "  make secrets-scan              Full repo secret scan (slow - full history)"
	@echo "  make secrets-install           Install pre-commit hook for automatic scanning"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean                     Clean build artifacts"
	@echo "  make clean-data                Clean data directories (CAREFUL!)"

# Local development with SQLite
dev:
	@bash scripts/run-local.sh python -m somali_dialect_classifier.orchestration.flows --pipeline $(PIPELINE) $(ARGS)

dev-all:
	@bash scripts/run-local.sh python -m somali_dialect_classifier.orchestration.flows --pipeline all

# Docker operations
docker-build:
	docker compose build

docker-up:
	docker compose --profile prod up -d

docker-down:
	docker compose --profile prod down

docker-logs:
	docker compose --profile prod logs -f

docker-test:
	docker compose run --rm somali-nlp-prod \
		python -m somali_dialect_classifier.orchestration.flows --pipeline wikipedia

docker-shell:
	docker compose run --rm somali-nlp-prod /bin/bash

# Testing
test:
	pytest tests/ -v

test-security:
	pytest tests/security/ -v

test-coverage:
	pytest tests/ --cov=src/somali_dialect_classifier --cov-report=html --cov-report=term

# Code quality
lint:
	ruff check src/ tests/
	mypy src/

format:
	ruff format src/ tests/

# Secret scanning
secrets-check:
	@echo "Scanning staged files for secrets..."
	@gitleaks protect --config .gitleaks.toml --staged --verbose

secrets-scan:
	@echo "Running full repository secret scan (this may take a while)..."
	@gitleaks detect --config .gitleaks.toml --verbose

secrets-install:
	@bash scripts/setup-gitleaks-hook.sh

# Maintenance
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage

clean-data:
	@echo "WARNING: This will delete all data directories!"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read confirm
	rm -rf data/raw/* data/processed/* data/staging/* data/ledger/*.db

# Database operations
db-backup:
	python scripts/backup_system.py

db-migrate:
	python scripts/migrate_sqlite_to_postgres.py

# Dashboard
dashboard-export:
	python scripts/export_dashboard_data.py

dashboard-serve:
	cd _site && python -m http.server 8000
