"""A module containing objects with various configuration settings."""
import warnings
from pathlib import Path

from ..database import BASE_DB_NAME
from .default_settings import Config, InstanceBasedConfig


class ProductionConfig(InstanceBasedConfig):
    """A configuration object with settings for production."""

    SECRET_KEY = "INSECURE"
    db_name = BASE_DB_NAME

    def __init__(self, db_path=None):
        super().__init__(db_path=db_path)
        if self.SECRET_KEY == "INSECURE":
            # Give an alert while the secret key remains insecure
            warnings.formatwarning = lambda msg, *args, **kwargs: f"\n{msg}\n"
            warnings.warn(
                "INSECURE: Production mode has not yet been fully configured; "
                "a secret key is required."
            )


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
