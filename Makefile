# Include variables
include config.mk

## develop 	: Install the package in development mode
.PHONY : develop 
develop :
	python setup.py develop

## install	: Install the package
.PHONY : install
install :
	python setup.py install

## package	: Bundle the package for distribution
.PHONY : package
package :
	python setup.py sdist bdist_wheel

## upload	: Upload the package to PyPI
.PHONY : upload
upload :
	python -m twine upload --skip-existing dist/*

## test		: Run tests
.PHONY : test
test :
	pytest --cov=. --cov-config=$(COVERAGE_CONFIG) --cov-report html

.PHONY : help
help : Makefile
	@sed -n 's/^##//p' $<
