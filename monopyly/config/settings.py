"""A module containing objects with various configuration settings."""
from pathlib import Path

from ..database import BASE_DB_NAME
from .default_settings import Config, InstanceBasedConfig


class ProductionConfig(InstanceBasedConfig):
    """A configuration object with settings for production."""

    SECRET_KEY = "INSECURE PRODUCTION TEST KEY"
    db_name = BASE_DB_NAME


class DevelopmentConfig(InstanceBasedConfig):
    """A configuration object with settings for development."""

    DEBUG = True
    SECRET_KEY = "development key"
    db_name = f"dev-{BASE_DB_NAME}"

    def __init__(self, db_path=None, preload_data_path=None):
        super().__init__(db_path=db_path)
        self.PRELOAD_DATA_PATH = preload_data_path

    @classmethod
    def configure_for_instance(cls, instance_path, **kwargs):
        """Instantiate the app based out of the given instance directory."""
        dev_data_path = Path(instance_path, "dev_data.sql")
        preload_data_path = dev_data_path if dev_data_path.exists() else None
        return super().configure_for_instance(
            instance_path, preload_data_path=preload_data_path, **kwargs
        )


class TestingConfig(Config):
    """A configuration object with settings for testing."""

    TESTING = True
    SECRET_KEY = "testing key"
    DATABASE_INTERFACE_ARGS = ()
    DATABASE_INTERFACE_KWARGS = {}
    WTF_CSRF_ENABLED = False

    def __init__(self, db_path=None, preload_data_path=None):
        super().__init__(db_path=db_path)
        self.PRELOAD_DATA_PATH = preload_data_path
