# Include variables
include config.mk


## install	: Install the package
.PHONY: install
install :
	@if [ ! -d "$(PRODUCTION_ENV)" ]; then $(PYTHON) -m venv $(PRODUCTION_ENV); fi
	@. $(PRODUCTION_ENV)/bin/activate; \
	pip install .


## develop 	: Install the package in development mode
.PHONY: develop
develop : env


## env		: Prepare a virtual environment to run the package
.PHONY: env
env : $(ENV)/.touchfile
	@echo "The environment ($(ENV)) is up to date."


# Create/update the virtual environment (based on `requirements.txt`, etc.)
# Uses touchfile as proxy for installed environment
$(ENV)/.touchfile : $(REQS) pyproject.toml
	@echo "Installing/updating the environment ($(ENV))."
	@if [ ! -d "$(ENV)" ]; then $(PYTHON) -m venv $(ENV); fi
	@. $(ENV_ACTIVATE); \
	pip install -r $(REQS) -e .
	@touch $(ENV)/.touchfile


## test		: Run tests
.PHONY: test
test : env
	@. $(ENV_ACTIVATE); \
	pytest $(COVERAGE_OPTIONS) \
		--cov-report term \
		--cov-report html


## format		: Format the package source code
.PHONY: format
format : env
	@. $(ENV_ACTIVATE); \
	isort $(PYTHON_FORMAT_DIRS); \
	black $(PYTHON_FORMAT_DIRS)


## format-diff	: See the differences that will be produced by formatting
.PHONY: format-diff
format-diff : env
	@. $(ENV_ACTIVATE); \
	isort --diff --color $(PYTHON_FORMAT_DIRS); \
	black --diff --color $(PYTHON_FORMAT_DIRS)


## package	: Bundle the package for distribution
.PHONY: package
package : env
	@. $(ENV_ACTIVATE); \
	hatch build


## upload		: Upload the package to PyPI
.PHONY: upload
upload : env
	@. $(ENV_ACTIVATE); \
	hatch publish --user __token__ --auth $$(cat .TOKEN)


## clean		: Clean all automatically generated files
.PHONY : clean
clean :
	@find . -type f -name '*.pyc' -delete
	@find . -type d -name '__pycache__' | xargs rm -rf
	@rm -rf .pytest_cache/
	@rm -rf $(PACKAGE_DIR)/_version.py
	@rm -rf $(ENV)
	@rm -rf htmlcov/
	@rm -rf dist/ *egg-info/
	@rm -rf instance/dev-monopyly.sqlite


.PHONY: help
help : Makefile
	@sed -n 's/^##//p' $<
