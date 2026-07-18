.PHONY: format lint typecheck test check-all ci

format:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff check .

typecheck:
	uv run mypy src/ tests/

test:
	uv run pytest

check-all: format lint typecheck test

ci:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy src/ tests/
	uv run pytest

