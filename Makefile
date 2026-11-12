.PHONY: setup up down data index lint typecheck test test-int check eval eval-gate api ui mcp-inspect

setup:
	uv sync --all-groups
	uv run pre-commit install

up:
	docker compose up -d --wait

down:
	docker compose down

data:
	@echo "TODO (Phase 1): download pinned snapshot, build eval sets"

index:
	@echo "TODO (Phase 3): embed history corpus + regulations into pgvector"

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy

test:
	uv run pytest

test-int:
	uv run pytest -m integration

check: lint typecheck test

eval:
	@echo "TODO (Phase 6): full eval run"

eval-gate:
	@echo "TODO (Phase 6): gated eval subset" && exit 1

api:
	@echo "TODO (Phase 5): run FastAPI"

ui:
	@echo "TODO (Phase 5): run Streamlit"

mcp-inspect:
	@echo "TODO (Phase 3): MCP Inspector"
