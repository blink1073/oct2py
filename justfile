# List available recipes
default:
    @just --list

# Install the project with all development dependencies
install:
    poetry install --with test,dev
    poetry run pre-commit install

# Run tests
test *args:
    poetry install --with test
    poetry run python -m pytest -n auto --dist=loadscope -vv {{args}}

# Run tests with coverage
cover *args:
    poetry install --with cover
    poetry run python -m pytest -n auto --dist=loadscope --doctest-modules -l --cov-report html --cov-report=xml --cov-report=term-missing --cov=oct2py --cov-fail-under 85 -vv {{args}}

# Run linters (ruff check + format)
lint:
    poetry install --with dev
    just pre-commit ruff-format
    just pre-commit ruff-check
    just pre-commit interrogate
    just pre-commit doc8
    just pre-commit validate-pyproject
    just pre-commit poetry-check

# Run type checking (mypy)
typing:
    poetry install --with typing
    poetry run mypy --install-types --non-interactive oct2py

# Build documentation
docs:
    poetry install --with docs
    poetry run mkdocs build --strict

# Serve documentation locally
docs-serve:
    poetry install --with docs
    poetry run mkdocs serve

# Open the example notebook interactively
run-notebook:
    poetry install --with test
    poetry run jupyter notebook example/octavemagic_extension.ipynb

# Run the example notebook as a test
test-notebook:
    poetry install --with test
    poetry run jupyter nbconvert --to notebook --execute --stdout example/octavemagic_extension.ipynb > /dev/null

# Run ASV benchmarks on HEAD (quick mode: one run per benchmark, ≤5 min)
benchmark:
    poetry install --with bench
    poetry run asv run --quick HEAD^!

# Compare benchmarks between the branch base commit and HEAD
benchmark-compare:
    poetry install --with bench
    poetry run asv machine --yes
    poetry run asv continuous $(git merge-base HEAD origin/main) HEAD --show-stderr

# Test opencv/oct2py compatibility
test-opencv:
    poetry install
    poetry run pip install opencv-python
    poetry run python scripts/test-opencv.py

# Run a pre-commit target
pre-commit *args:
    poetry install --with dev
    poetry run pre-commit run --all-files {{args}}
