.PHONY: all clean test cover release

all:  
	make clean
	python setup.py install

clean:
	rm -rf build
	rm -rf dist
	find . -name "*.pyc" -o -name "*.py,cover"| xargs rm -f

test: 
	make clean
	python setup.py build
	cd build
	nosetests --exe -v --with-doctest 
	cd ..
	rm -rf build	
	python setup.py check -r
	
cover: 
	make clean
	pip install nose-cov
	nosetests --exe --with-cov --cov oct2py --cov-config .coveragerc oct2py
	coverage annotate

release:
	make clean
	pip install sphinx-pypi-upload
	pip install numpydoc
	python setup.py register
	python setup.py bdist_wininst --target-version=2.7 upload
	python setup.py bdist_wininst --target-version=3.2 upload
	python setup.py bdist_wininst --target-version=3.3 upload
	python setup.py bdist_wheel upload
	python setup.py sdist --formats=gztar,zip upload
	pushd docs
	make html
	popd
	python setup.py upload_sphinx
	echo "Make sure to tag the branch"
	echo "Make sure to push to hg"

gh-pages:
	git checkout master
	git pull origin master
	rm -rf ../temp_docs
	mkdir ../temp_docs
	rm -rf docs/build
	-make -C docs html
	cp -R docs/build/html/ ../temp_docs
	mv ../temp_docs/html ../temp_docs/docs
	git checkout gh-pages
	rm -rf docs
	cp -R ../enaml_docs/docs/ .
	git add .
	git commit -m "rebuild docs"
	git push upstream-rw gh-pages
	rm -rf ../enaml_docs
	git checkout master
	rm docs/.buildinfo

