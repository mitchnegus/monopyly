"""A module containing objects with various configuration settings."""

from dry_foundation.config.settings import DevelopmentConfig as _DevelopmentConfig
from dry_foundation.config.settings import ProductionConfig as _ProductionConfig
from dry_foundation.config.settings import TestingConfig as _TestingConfig

from .database import BASE_DB_NAME

CONFIG_FILENAME = f"monopyly-config.json"


class ProductionConfig(_ProductionConfig):
    """A configuration object with settings for production."""

    config_filename = CONFIG_FILENAME
    db_name = BASE_DB_NAME


class DevelopmentConfig(_DevelopmentConfig):
    """A configuration object with settings for development."""

    config_filename = CONFIG_FILENAME
    db_name = f"dev-{BASE_DB_NAME}"


class TestingConfig(_TestingConfig):
    """A configuration object with settings for testing."""

    config_filename = CONFIG_FILENAME
