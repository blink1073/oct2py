.PHONY: all clean test

all:
	rm -r build
	find . -name "*.so" -o -name "*.pyc" -o -name "*.pyx.md5" | xargs rm -f
	python setup.py install

clean:
	find . -name "*.so" -o -name "*.pyc" -o -name "*.pyx.md5" | xargs rm -f

test:
	pushd ~
	nosetsests lib3to2
	popd
