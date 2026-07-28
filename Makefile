.PHONY: validate dev-up dev-down

validate:
	python3 scripts/validate_repo.py

dev-up:
	docker compose -f infrastructure/docker/compose.dev.yaml up -d

dev-down:
	docker compose -f infrastructure/docker/compose.dev.yaml down
