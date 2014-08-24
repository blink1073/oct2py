# Note: This is meant for Oct2Py developer use only
.PHONY: all clean test cover release gh-pages

export TEST_ARGS=--exe -v --with-doctest
export KILL_OCTAVE="from oct2py import kill_octave; kill_octave()"

all: clean
	python setup.py install

clean:
	rm -rf build
	rm -rf dist
	find . -name "*.pyc" -o -name "*.py,cover"| xargs rm -f
	python -c $(KILL_OCTAVE)
	killall -9 nosetests; true

test: clean
	python setup.py build
	export PYTHONWARNINGS="all"; cd build; nosetests $(TEST_ARGS)
	make clean

cover: clean
	pip install nose-cov
	nosetests $(TEST_ARGS) --with-cov --cov oct2py oct2py
	coverage annotate

release:
	pip install wheel
	python setup.py register
	python setup.py bdist_wheel upload
	python setup.py sdist --formats=gztar,zip upload
	git tag v`python -c "import oct2py;print(oct2py.__version__)"`
	git push origin master --all

gh-pages: clean
	pip install sphinx-bootstrap-theme numpydoc sphinx ghp-import
	git checkout master
	git pull origin master
	make -C docs html
	export MSG="Generated gh-pages for `git log master -1 --pretty=short --abbrev-commit`"
	ghp-import -n -p -m $(MSG) docs/_build/html
