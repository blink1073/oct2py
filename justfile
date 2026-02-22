# List available recipes
default:
    @just --list

# Install the project with all development dependencies
install:
    uv sync --all-groups

# Run tests
test *args:
    uv run --group test python -m pytest -vv {{args}}

# Run tests with coverage
cover *args:
    uv run --group cover python -m pytest --doctest-modules -l --cov-report html --cov-report=xml --cov=oct2py --cov-fail-under 85 -vv {{args}}

# Run linters (ruff check + format)
lint:
    uv run --group lint pre-commit run --all-files ruff
    uv run --group lint pre-commit run --all-files ruff-format

# Run type checking (mypy via pre-commit)
typing:
    uv run --group lint pre-commit run --all-files --hook-stage manual mypy

# Build documentation
docs:
    uv run --group docs make -C docs html SPHINXOPTS='-W'
