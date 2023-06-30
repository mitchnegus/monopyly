"""Default configuration settings."""
from pathlib import Path


class Config:
    """A base configuration object with some default settings."""

    def __init__(self, db_path=None):
        if db_path:
            self.DATABASE = db_path

    @property
    def DATABASE(self):
        return self._database

    @DATABASE.setter
    def DATABASE(self, value):
        # Ensure that the database path is always set as a `pathlib.Path` object
        self._database = Path(value)


class InstanceBasedConfig(Config):
    """A base configuration object for app modes using instance directories."""

    TESTING = False
    db_name = None

    @classmethod
    def configure_for_instance(cls, instance_path, **kwargs):
        """Instantiate the app based out of the given instance directory."""
        instance_path = Path(instance_path)
        instance_path.mkdir(parents=True, exist_ok=True)
        db_path = Path(instance_path, cls.db_name) if cls.db_name else None
        return cls(db_path=db_path, **kwargs)
