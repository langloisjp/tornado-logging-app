test:
	coverage run --source . --omit setup.py,tests/\* -m unittest discover tests
	coverage html
	coverage report

install:
	python setup.py install

spkg:
	python setup.py sdist
