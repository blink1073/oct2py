# Contributing to Oct2Py

## Installation and Test

Oct2Py uses [uv](https://docs.astral.sh/uv/) for dependency management and
[just](https://just.systems/) as a command runner.

To install all development dependencies:

```
uv sync --all-groups
```

To run the tests:

```
just test
```

\<<\<<\<<< HEAD
Tests run in parallel across CPU cores (one process per test module) using
[pytest-xdist](https://pytest-xdist.readthedocs.io/). To disable parallelism
(e.g. for debugging):

```
just test -n0
```

To run a single test:

```
just test tests/test_misc.py::test_name
```

||||||| a4b9bd2

# Contributing to Oct2Py

## Installation and Test

Oct2Py uses [uv](https://docs.astral.sh/uv/) for dependency management and
[just](https://just.systems/) as a command runner.

To install all development dependencies:

```
uv sync --all-groups
```

To run the tests:

```
just test
```

To run tests with coverage:

```
just cover
```

## Linters

Oct2Py uses [pre-commit](https://pypi.org/project/pre-commit/)
for managing linting of the codebase.
`pre-commit` performs various checks on all files in Oct2Py and uses tools
that help follow a consistent code style within the codebase.

To set up `pre-commit` locally, run:

```
uv run --group lint pre-commit install
```

To run linters:

```
just lint
```

To run type checking:

```
just typing
```

## Documentation

To build the docs:

```
just docs
```

\=======

> > > > > > > 43e5a82def4daee45bb4da25169daada6e7e24f1
> > > > > > > To run tests with coverage:

```
just cover
```

## Linters

Oct2Py uses [pre-commit](https://pypi.org/project/pre-commit/)
for managing linting of the codebase.
`pre-commit` performs various checks on all files in Oct2Py and uses tools
that help follow a consistent code style within the codebase.

To set up `pre-commit` locally, run:

```
uv run --group lint pre-commit install
```

To run linters:

```
just lint
```

To run type checking:

```
just typing
```

## Documentation

To build the docs:

```
just docs
```
