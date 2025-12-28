.PHONY: test lint install-hooks build clean help

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

test: ## Run tests with coverage
	pytest -v --cov=checkend --cov-report=term-missing

lint: ## Run linter (ruff)
	ruff check .
	ruff format --check .

format: ## Format code with ruff
	ruff check --fix .
	ruff format .

install-hooks: ## Install git hooks
	./scripts/install-hooks.sh

install: ## Install package in development mode
	pip install -e ".[dev]"

build: ## Build package
	python -m build

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

all: lint test ## Run lint and tests
