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
    uv run --group cover python -m coverage run -m pytest -l -vv {{args}}
    uv run --group cover python -m coverage report --fail-under=85
    uv run --group cover python -m coverage html
    uv run --group cover python -m coverage xml

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
