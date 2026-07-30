.PHONY: validate dev-up dev-down

validate:
	python3 scripts/validate_repo.py
	uv run ruff check devsembly tests scripts/*.py
	uv run ruff format --check devsembly tests scripts/*.py
	uv run mypy devsembly
	uv run pytest -q
	npx --yes markdownlint-cli2@0.19.0 '**/*.md'
	python3 scripts/check_markdown_links.py

dev-up:
	docker compose -f infrastructure/docker/compose.dev.yaml up -d

dev-down:
	docker compose -f infrastructure/docker/compose.dev.yaml down
