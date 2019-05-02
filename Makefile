# Note: This is meant for Oct2Py developer use only
.PHONY: all clean test cover release gh-pages docs

NAME:=$(shell python setup.py --name 2>/dev/null)
VERSION:=$(shell python setup.py --version 2>/dev/null)
KILL_PROC="from ${NAME} import kill_octave; kill_octave()"

all: clean
	python setup.py install

clean:
	rm -rf build
	rm -rf dist
	find . -name "*.pyc" -o -name "*.py,cover"| xargs rm -f
	python -c $(KILL_PROC)
	killall -9 py.test; true

test: clean
	pip install -q pytest
	export PYTHONWARNINGS="all"; py.test
	make clean
	jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=60 --stdout example/octavemagic_extension.ipynb > /dev/null;

cover: clean
	pip install -q pytest codecov pytest-cov
	py.test -l --cov-report html --cov=${NAME}

release: clean
	pip install -q wheel
	git commit -a -m "Release ${VERSION}"; true
	python setup.py register
	rm -rf dist
	python setup.py bdist_wheel --universal
	python setup.py sdist
	git tag v${VERSION}
	git push origin --all
	git push origin --tags
	twine upload dist/*

docs: clean
	pip install -q sphinx-rtd-theme numpydoc sphinx
	export SPHINXOPTS=-W; make -C docs html
	export SPHINXOPTS=-W; make -C docs linkcheck
