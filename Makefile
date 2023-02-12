# Include variables
include config.mk


## install	: Install the package
.PHONY: install
install:
	$(PIP) install .


## develop 	: Install the package in development mode
.PHONY: develop
develop:
	$(PIP) install -e .


## env		: Prepare a virtual environment to run the package
.PHONY: env
env: $(ENV)/.touchfile
	@echo "The environment ($(ENV)) is up to date."


# Create/update the virtual environment (based on `requirements.txt`, etc.)
# Uses touchfile as proxy for installed environment
$(ENV)/.touchfile : $(REQS) setup.py
	@echo "Installing/updating the environment ($(ENV))."
	@if [ ! -d "$(ENV)" ]; then $(PYTHON) -m venv $(ENV); fi
	@. $(ENV_ACTIVATE); \
	$(PIP) install -r $(REQS) -e .
	@touch $(ENV)/.touchfile


## test		: Run tests
.PHONY: test
test: env
	@. $(ENV_ACTIVATE); \
	pytest $(COVERAGE_OPTIONS) \
		--cov-report term \
		--cov-report html


## format		: Format the package source code
.PHONY: format
format:
	@isort $(PYTHON_FORMAT_FILES)


## format-diff	: See the differences that will be produced by formatting
.PHONY: format-diff
format-diff:
	@isort --diff --color $(PYTHON_FORMAT_FILES)


## package	: Bundle the package for distribution
.PHONY: package
package:
	$(PYTHON) setup.py sdist bdist_wheel


## upload		: Upload the package to PyPI
.PHONY: upload
upload : env
	@. $(ENV_ACTIVATE); \
	$(PYTHON) -m twine upload --skip-existing dist/*


## clean		: Clean all automatically generated files
.PHONY : clean
clean :
	@rm -rf instance/dev-monopyly.sqlite
	@rm -rf build/ dist/ *egg-info/
	@rm -rf $(ENV)


.PHONY: help
help: Makefile
	@sed -n 's/^##//p' $<
