# Note: This is meant for Oct2Py developer use only
.PHONY: all clean test cover release gh-pages docs

export NAME=`python setup.py --name 2>/dev/null`
export VERSION=`python setup.py --version 2>/dev/null`
export KILL_PROC="from $(NAME) import kill_octave; kill_octave()"
export GHP_MSG="Generated gh-pages for `git log master -1 --pretty=short --abbrev-commit`"

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

cover: clean
	pip install -q pytest codecov pytest-cov
	py.test -l --cov-report html --cov=$(NAME)

release: clean gh-pages
	pip install -q wheel
	python setup.py register
	rm -rf dist
	python setup.py bdist_wheel --universal
	python setup.py sdist
	git commit -a -m "Release $(VERSION)"; true
	git tag v$(VERSION)
	git push origin --all
	git push origin --tags
	twine upload dist/*
	printf '\nUpgrade oct2py-feedstock with release and sha256 sum:'
	shasum -a 256 dist/*.tar.gz

docs: clean
	pip install -q sphinx-bootstrap-theme numpydoc sphinx ghp-import
	export SPHINXOPTS=-W; make -C docs html
	export SPHINXOPTS=-W; make -C docs linkcheck

gh-pages:
	git checkout master
	git pull origin master
	cp oct2py/tests/*.m example
	rm example/script_error.m; true
	git commit -a -m "Keep examples in sync"; true
	git push origin; true
	make docs
	ghp-import -n -p -m $(GHP_MSG) docs/_build/html
