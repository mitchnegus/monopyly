"""A module containing objects with various configuration settings."""
from monopyly.config.default_settings import Config


class DevelopmentConfig(Config):
    """A configuration object with settings for development."""

    DEBUG = True
    SECRET_KEY = "development key"

    def __init__(self, db_path=None, preload_data_path=None):
        super().__init__(db_path=db_path)
        self.PRELOAD_DATA_PATH = preload_data_path


class TestingConfig(Config):
    """A configuration object with settings for testing."""

    TESTING = True
    SECRET_KEY = "testing key"
    WTF_CSRF_ENABLED = False

    def __init__(self, db_path=None, preload_data_path=None):
        super().__init__(db_path=db_path)
        self.PRELOAD_DATA_PATH = preload_data_path


class ProductionConfig(Config):
    """A configuration object with settings for production."""

    SECRET_KEY = "INSECURE PRODUCTION TEST KEY"
