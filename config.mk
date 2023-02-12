# Coverage configuration
PYTHON = python3.9
PIP = $(PYTHON) -m pip
# Package
PACKAGE = monopyly
# Requirements files
REQS = requirements.txt
# Package environment (for building and testing)
ENV = monopyly-env
ENV_BIN = $(ENV)/bin
ENV_ACTIVATE = $(ENV_BIN)/activate

# Testing
COVERAGE_OPT_LOCATION = --cov=.
COVERAGE_OPT_CONFIG = --cov-config=.coveragerc
COVERAGE_OPTIONS = $(COVERAGE_OPT_LOCATION) $(COVERAGE_OPT_CONFIG)

# Format files
PYTHON_FORMAT_FILES = monopyly/ test/ setup.py
