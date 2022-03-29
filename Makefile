# Note: This is meant for Oct2Py developer use only
.PHONY: all clean test cover release gh-pages docs

NAME:=$(shell python setup.py --name 2>/dev/null)
VERSION:=$(shell python setup.py --version 2>/dev/null)
KILL_PROC="from ${NAME} import kill_octave; kill_octave()"

all: clean
	python setup.py install


install: clean
	pip install -e .[docs,test]
	pre-commit install
	octave --eval "pkg install -forge control"
	octave --eval "pkg install -forge signal"

clean:
	rm -rf build
	rm -rf dist
	find . -name "*.pyc" -o -name "*.py,cover"| xargs rm -f
	python -c $(KILL_PROC); true
	killall -9 pytest; true

test: clean
	pip install -q pytest
	export PYTHONWARNINGS="all"; pytest --doctest-modules
	make clean
	jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=60 --stdout example/octavemagic_extension.ipynb > /dev/null;

cover: clean
	pip install -q pytest codecov pytest-cov
	pytest --doctest-modules -l --cov-report html --cov-report=xml --cov=${NAME}

release_prep: clean
	pip install -q wheel twine
	git commit -a -m "Release ${VERSION}"; true
	python setup.py bdist_wheel --universal
	python setup.py sdist
	twine check dist/*

release: release_prep
	git tag v${VERSION}
	git push origin --all
	git push origin --tags
	twine upload dist/*

docs: clean
	pip install -q sphinx-rtd-theme numpydoc sphinx
	export SPHINXOPTS=-W; make -C docs html
	export SPHINXOPTS=-W; make -C docs linkcheck || export SPHINXOPTS=-W; make -C docs linkcheck
