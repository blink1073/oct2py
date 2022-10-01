Contributing to Oct2Py
=======================

Installation and Test
---------------------

To install and run tests locally, run::

    pip install -e ".[test]"
    pytest .

Linters
-------

Oct2Py uses `pre-commit <https://pypi.org/project/pre-commit/>`_
for managing linting of the codebase.
``pre-commit`` performs various checks on all files in Oct2Py and uses tools
that help follow a consistent code style within the codebase.

To set up ``pre-commit`` locally, run::

    pip install pre-commit
    pre-commit install

To run ``pre-commit`` manually, run::

    pre-commit run --all-files
