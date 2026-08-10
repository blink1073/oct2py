# List available recipes
default:
    @just --list

# Install the project with all development dependencies
install:
    poetry sync --only main,test,dev
    poetry run pre-commit install

# Run tests
test *args:
    poetry sync --only main,test
    poetry run python -m pytest -n auto --dist=loadscope -vv {{args}}

# Run tests sequentially (no xdist) — mirrors the sdist test environment
test-seq *args:
    poetry sync --only main,test
    poetry run python -m pytest -v {{args}}

# Run tests with coverage
cover *args:
    poetry sync --only main,cover
    poetry run python -m pytest -n auto --dist=loadscope --doctest-modules -l --cov-report html --cov-report=xml --cov-report=term-missing --cov=oct2py --cov-fail-under 85 -vv {{args}}

# Run all pre-commit hooks
lint *args:
    poetry sync --only main,dev
    poetry run pre-commit run --all-files {{args}}

# Run type checking (mypy)
typing:
    poetry sync --only main,typing
    poetry run mypy --install-types --non-interactive oct2py

# Build documentation
docs:
    poetry sync --only main,docs
    poetry run mkdocs build --strict

# Serve documentation locally
docs-serve:
    poetry sync --only main,docs
    poetry run mkdocs serve

# Open the example notebook interactively
run-notebook:
    poetry sync --only main,test
    poetry run jupyter notebook example/octavemagic_extension.ipynb

# Run the example notebook as a test
test-notebook:
    poetry sync --only main,test
    poetry run jupyter nbconvert --to notebook --execute --stdout example/octavemagic_extension.ipynb > /dev/null

# Run ASV benchmarks on HEAD (quick mode: one run per benchmark, ≤5 min)
benchmark:
    poetry sync --only main,bench
    poetry run asv run --quick HEAD^!

# Compare benchmarks between the branch base commit and HEAD
benchmark-compare:
    poetry sync --only main,bench
    poetry run asv machine --yes
    poetry run asv continuous $(git merge-base HEAD origin/main) HEAD --show-stderr

# Test opencv/oct2py compatibility
test-opencv:
    poetry sync --only main
    poetry run pip install opencv-python
    poetry run python scripts/test-opencv.py

# Build and run the PyInstaller test app
pyinstaller-test:
    poetry sync --only main,pyinstaller
    poetry run python pyinstaller_test/test_build.py

# Run all pre-commit hooks, including manual-stage hooks
lint-all *args:
    poetry sync --only main,dev
    poetry run pre-commit run --all-files --hook-stage manual {{args}}
