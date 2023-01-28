# Include variables
include config.mk


## develop 	: Install the package in development mode
.PHONY: develop
develop:
	$(PIP) install -e .


## install	: Install the package
.PHONY: install
install:
	$(PIP) install .


## package	: Bundle the package for distribution
.PHONY: package
package:
	$(PYTHON) setup.py sdist bdist_wheel


## upload		: Upload the package to PyPI
.PHONY: upload
upload :
	$(PYTHON) -m twine upload --skip-existing dist/*


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
	pytest $(COVERAGE_OPTIONS) --cov-report html


.PHONY: help
help: Makefile
	@sed -n 's/^##//p' $<
