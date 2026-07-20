.PHONY: format lint typecheck test check-all ci docs-sync-check config-doc-sync-check

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

# Warn-only doc sync vs origin/main (never fails; not part of `make ci`)
docs-sync-check:
	bash scripts/check-doc-sync.sh

# Warn-only: LiltConfig field names vs docs/reference/config.md (never fails; not part of `make ci`)
config-doc-sync-check:
	bash scripts/check-config-doc-sync.sh

