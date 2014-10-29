all:caio.so

caio.so: caio.pxd aio.pyx
	python setup.py build_ext --inplace

clean:
	rm -rf *.so *.pyc build aio.c test.c

