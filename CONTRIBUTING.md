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

## Benchmarking

Performance benchmarks live in `benchmarks/benchmarks.py` and are run with
[ASV (Airspeed Velocity)](https://asv.readthedocs.io/).

To run benchmarks on the current commit (quick mode — one sample per
benchmark, completes in under five minutes):

```
just benchmark
```

To compare the current branch against its base commit:

```
just benchmark-compare
```

The comparison uses `git merge-base HEAD main` as the baseline and flags any
benchmark that changes by more than 10% (ASV's default `--factor 1.1`).

### Adding Benchmarks

Benchmarks follow the same patterns as `tests/test_usage.py`. Each class
uses `setup` / `teardown` to start and stop an `Oct2Py` session (setup time
is excluded from measurements):

```python
class MyBenchmarks:
    def setup(self):
        self.oc = Oct2Py()

    def teardown(self):
        self.oc.exit()

    def time_my_operation(self):
        self.oc.eval("ones(10)")
```

ASV discovers any method prefixed with `time_` automatically.
