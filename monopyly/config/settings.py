"""A module containing objects with various configuration settings."""
from monopyly.config.default_settings import Config


class DevelopmentConfig(Config):
    """A configuration object with settings for development."""
    DEBUG = True
    SECRET_KEY = "development key"


class TestingConfig(Config):
    """A configuration object with settings for testing."""
    TESTING = True
    SECRET_KEY = "testing key"
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """A configuration object with settings for production."""
    SECRET_KEY = "INSECURE PRODUCTION TEST KEY"

