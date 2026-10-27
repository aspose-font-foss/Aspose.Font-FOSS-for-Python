.PHONY: help install test lint lint-fix build publish publish-test clean all

UV_CACHE_DIR ?= /tmp/uv-cache

# Default target
all: lint test build

##@ Help

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

install: ## Install package and dev dependencies
	pip install -e ".[dev]"

test: ## Run all tests
	uv run python -m pytest tests/ -v

lint: ## Run linter (ruff check)
	uv run python -m ruff check src/

lint-fix: ## Run linter with auto-fix
	uv run python -m ruff check src/ --fix

##@ Build and Publish

build: ## Build wheel and sdist
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run --with build python -m build

publish-test: ## Publish to TestPyPI (requires dist/* from `make build`)
	uv run --with twine python -m twine upload --repository testpypi dist/*

publish: ## Publish to PyPI (requires dist/* from `make build`)
	uv run --with twine python -m twine upload dist/*

##@ Maintenance

clean: ## Remove build artifacts and caches
	rm -rf dist/ build/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	find . -name "*.pyc" -delete


