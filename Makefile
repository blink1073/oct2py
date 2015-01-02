# Note: This is meant for Oct2Py developer use only
.PHONY: all clean test cover release gh-pages

export TEST_ARGS=--exe -v --with-doctest
export NAME=oct2py
export KILL_PROC="from $(NAME) import kill_octave; kill_octave()"
export GHP_MSG="Generated gh-pages for `git log master -1 --pretty=short --abbrev-commit`"
export VERSION=`python -c "import $(NAME); print($(NAME).__version__)"`

all: clean
	python setup.py install

clean:
	rm -rf build
	rm -rf dist
	find . -name "*.pyc" -o -name "*.py,cover"| xargs rm -f
	python -c $(KILL_PROC)
	killall -9 nosetests; true

test: clean
	python setup.py build
	export PYTHONWARNINGS="all"; cd build; nosetests $(TEST_ARGS)
	make clean

cover: clean
	pip install nose-cov
	nosetests $(TEST_ARGS) --with-cov --cov $(NAME) $(NAME)
	coverage annotate

release: test gh-pages
	pip install wheel
	python setup.py register
	python setup.py bdist_wheel upload
	python setup.py sdist --formats=gztar,zip upload
	git tag v$(VERSION)
	git push origin --all
	git push origin --tags

gh-pages: clean
	pip install sphinx-bootstrap-theme numpydoc sphinx ghp-import
	git checkout master
	git pull origin master
	cp oct2py/tests/*.m example
	git commit -a -m "Keep examples in sync"; true
	git push origin; true
	make -C docs html
	ghp-import -n -p -m $(GHP_MSG) docs/_build/html
