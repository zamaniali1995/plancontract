.PHONY: help sync test lint typecheck format format-check ci build clean

help:
	@echo "Targets: sync test lint typecheck format format-check ci build clean"

sync:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src/plancontract

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

format-check:
	uv run ruff format --check src tests
	uv run ruff check src tests

ci: sync format-check lint typecheck test build

build:
	uv build

clean:
	rm -rf dist build .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
