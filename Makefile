.PHONY: all clean test cover

all:  
	make clean
	python setup.py install

clean:
	rm -rf build
	find . -name "*.pyc" -o -name "*.py,cover"| xargs rm -f

test: 
	make clean
	python runtests.py
	python setup.py check -r
	
cover: 
	make clean
	coverage run --source oct2py -m py.test -v
	coverage report

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
