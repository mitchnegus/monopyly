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

## test		: Run tests
.PHONY : test
test :
	pytest --cov=. --cov-config=$(COVERAGE_CONFIG) --cov-report html

.PHONY : help
help : Makefile
	@sed -n 's/^##//p' $<
