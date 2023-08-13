# Coverage configuration
PYTHON = python3.9
PIP = $(PYTHON) -m pip
# Package
PACKAGE = monopyly
PACKAGE_DIR = $(PACKAGE)
# Testing
TEST_DIR = tests

# Requirements files
REQS = requirements.txt
# Package environment (for building and testing)
ENV = monopyly-env
ENV_BIN = $(ENV)/bin
ENV_ACTIVATE = $(ENV_BIN)/activate

COVERAGE_OPT_LOCATION = --cov=.
COVERAGE_OPTIONS = $(COVERAGE_OPT_LOCATION)

# Format files
PYTHON_FORMAT_DIRS = $(PACKAGE_DIR) $(TEST_DIR)
