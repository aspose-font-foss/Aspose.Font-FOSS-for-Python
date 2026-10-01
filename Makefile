.PHONY: help install test lint lint-fix build publish publish-test clean docs serve-website token-estimate token-report token-stage token-sync-completed all

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

docs: ## Placeholder for documentation generation
	@echo "open website/index.html"

serve-website: ## Serve website/ locally at http://127.0.0.1:8000 (docs at /docs/)
	uv run python -m http.server 8000 --directory website

##@ Reporting

TASK_ID ?= FONT-000
TASK_TITLE ?= Example Task
TASK_STAGE ?= completion
ESTIMATED_TOKENS ?= 0
RUN_DURATION_MS ?= 0
ITEMS_DISCOVERED ?= 1
ITEMS_FAILED ?= 0
ITEMS_SUCCEEDED ?= 1
API_CALLS_COUNT ?= 0

token-estimate: ## Store an assistant-estimated token count for TASK_ID
	uv run aspose-font-reporting estimate "$(TASK_ID)" "$(ESTIMATED_TOKENS)" --title "$(TASK_TITLE)" --stage "$(TASK_STAGE)"

token-report: ## Send the completion report for TASK_ID using the stored estimate
	uv run aspose-font-reporting report "$(TASK_ID)" --title "$(TASK_TITLE)" --stage "$(TASK_STAGE)" --run-duration-ms "$(RUN_DURATION_MS)" --items-discovered "$(ITEMS_DISCOVERED)" --items-failed "$(ITEMS_FAILED)" --items-succeeded "$(ITEMS_SUCCEEDED)" --api-calls-count "$(API_CALLS_COUNT)"

token-stage: ## Store and send a stage token report for TASK_ID/TASK_STAGE
	uv run aspose-font-reporting stage "$(TASK_ID)" "$(TASK_STAGE)" "$(ESTIMATED_TOKENS)" --title "$(TASK_TITLE)" --run-duration-ms "$(RUN_DURATION_MS)" --items-discovered "$(ITEMS_DISCOVERED)" --items-failed "$(ITEMS_FAILED)" --items-succeeded "$(ITEMS_SUCCEEDED)" --api-calls-count "$(API_CALLS_COUNT)"

token-sync-completed: ## Send missing reports for completed backlog tasks using stored estimates
	uv run aspose-font-reporting sync-completed --run-duration-ms "$(RUN_DURATION_MS)" --items-discovered "$(ITEMS_DISCOVERED)" --items-failed "$(ITEMS_FAILED)" --items-succeeded "$(ITEMS_SUCCEEDED)" --api-calls-count "$(API_CALLS_COUNT)"
