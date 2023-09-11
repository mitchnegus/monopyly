PYTHON = python3.10
# Package
PACKAGE = monopyly
PACKAGE_DIR = $(PACKAGE)

# Requirements files
REQS = requirements.txt
# Package environment (for building and testing)
ENV = $(PACKAGE)-env
ENV_BIN = $(ENV)/bin
ENV_ACTIVATE = $(ENV_BIN)/activate
# Production environment (for deployment)
PRODUCTION_ENV = $(PACKAGE)-production-env

# Testing
TEST_DIR = tests
# Coverage configuration
COVERAGE_OPT_LOCATION = --cov=.
COVERAGE_OPTIONS = $(COVERAGE_OPT_LOCATION)

# Format files
PYTHON_FORMAT_DIRS = $(PACKAGE_DIR) $(TEST_DIR)
