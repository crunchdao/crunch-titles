PYTHON=python3
PIP=$(PYTHON) -m pip

install:
	$(PIP) install -e .[test]

uninstall:
	$(PIP) uninstall crunch-titles

test:
	$(PYTHON) -m pytest -vv

test-with-coverage:
	$(PYTHON) -m pytest --cov=crunch_titles --cov-report=html -vv

build:
	rm -rf build *.egg-info dist
	$(PYTHON) setup.py sdist bdist_wheel

.PHONY: install uninstall test build
