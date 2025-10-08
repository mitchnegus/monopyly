PYTHON = python3
# Package
PACKAGE = monopyly
PACKAGE_DIR = $(PACKAGE)

# Requirements files
REQS = requirements.txt
# Package environment (for building and testing)
ENV = $(PACKAGE)-env
ENV_BIN = $(ENV)/bin
# Production environment (for deployment)
PRODUCTION_ENV = $(PACKAGE)-production-env

# Testing
TEST_DIR = tests

# Lint/format files
PYTHON_LINT_DIRS = $(PACKAGE_DIR) $(TEST_DIR)
PYTHON_FORMAT_DIRS = $(PACKAGE_DIR) $(TEST_DIR)
