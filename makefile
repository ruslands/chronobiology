.PHONY: test
test:
	pytest tests/

.PHONY: isort
isort:
	poetry run isort --recursive --verbose .

.PHONY: isort.check
isort.check:
	poetry run isort --recursive . --diff --check-only

.PHONY: ruff
ruff:
	ruff chronobiology/ tests/ --verbose

.PHONY: ruff.check
ruff.check:
	poetry run ruff chronobiology/ tests/ --diff

.PHONY: black
black:
	poetry run black chronobiology/ tests/ --verbose

.PHONY: black.check
black.check:
	poetry run black chronobiology/ tests/ --check --extend-exclude builds


