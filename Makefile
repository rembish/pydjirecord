VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy

SRC := src/ tests/

.PHONY: help venv install format lint typecheck test integration check build clean distclean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

venv: ## Create virtualenv
	python3 -m venv $(VENV)

install: venv ## Install package in editable mode with dev dependencies
	$(PIP) install -e ".[dev]"

format: ## Format code (ruff format + autofix)
	$(RUFF) format $(SRC)
	$(RUFF) check --fix $(SRC)

lint: ## Lint code (ruff check)
	$(RUFF) check $(SRC)

typecheck: ## Run mypy strict type checking
	$(MYPY) src/

test: ## Run tests with coverage
	$(PYTEST)

integration: ## Run integration + mutation-regression tests against a private corpus (set DJI_LOGS_DIR=)
	DJI_LOGS_DIR=$(DJI_LOGS_DIR) $(PYTEST) -m integration --no-cov -xvs tests/test_djilog.py tests/test_mutation_regression.py

check: format lint typecheck test ## Run all checks (format + lint + typecheck + test)

build: ## Build distribution packages
	$(PYTHON) -m build

clean: ## Remove build/cache artifacts
	rm -rf .mypy_cache .pytest_cache .ruff_cache .coverage htmlcov/ dist/ build/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +

distclean: clean ## Remove everything including venv
	rm -rf $(VENV)
