# Note: This is meant for Oct2Py developer use only
.PHONY: all clean test cover release gh-pages

export TEST_ARGS=--exe -v
export KILL_OCTAVE="from oct2py import kill_octave; kill_octave())"

all:
	make clean
	python setup.py install

clean:
	rm -rf build
	rm -rf dist
	find . -name "*.pyc" -o -name "*.py,cover"| xargs rm -f
	python -c $(KILL_OCTAVE)
	killall -9 nosetests; true

test:
	make clean
	python setup.py build
	export PYTHONWARNINGS="all"; cd build; nosetests $(TEST_ARGS)
	make clean

cover:
	make clean
	pip install nose-cov
	nosetests -v --exe --with-cov --cov oct2py oct2py
	coverage annotate

release:
	make clean
	pip install wheel
	python setup.py register
	python setup.py bdist_wheel upload
	python setup.py sdist --formats=gztar,zip upload
	echo "*** Do not forget to add a tag"
	echo "*** Do not forget to 'make gh-pages'"

gh-pages:
	pip install sphinx-bootstrap-theme
	pip install numpydoc
	git checkout master
	git pull origin master
	rm -rf ../temp_docs
	mkdir ../temp_docs
	rm -rf docs/build
	make -C docs html
	cp -R docs/_build/html/ ../temp_docs
	mv ../temp_docs/html ../temp_docs/docs
	git checkout gh-pages
	rm -rf docs
	cp -R ../temp_docs/docs/ .
	git add docs
	git commit -m "rebuild docs"
	git push origin gh-pages
	rm -rf ../temp_docs
	git checkout master

