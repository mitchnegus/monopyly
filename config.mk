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

# Format files
PYTHON_FORMAT_DIRS = $(PACKAGE_DIR) $(TEST_DIR)
