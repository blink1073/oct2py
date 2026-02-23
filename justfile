# List available recipes
default:
    @just --list

# Install the project with all development dependencies
install:
    uv sync
    uv tool run prek install

# Run tests
test *args:
    uv run --group test python -m pytest -vv {{args}}

# Run tests with coverage
cover *args:
    uv run --group cover python -m pytest --doctest-modules -l --cov-report html --cov-report=xml --cov=oct2py --cov-fail-under 85 -vv {{args}}

# Run linters (ruff check + format)
lint:
    just pre-commit ruff
    just pre-commit ruff-format

# Run type checking (mypy via pre-commit)
typing:
    just pre-commit --hook-stage manual mypy

# Build documentation
docs:
    uv run --group docs make -C docs html SPHINXOPTS='-W'

# Run a pre-commit target
pre-commit *args:
    uv tool run prek --all-files {{args}}