"""Default configuration settings."""
import json
from pathlib import Path

CONFIG_FILENAME = f"monopyly-config.json"
DEFAULT_CONFIG_PATH = Path("/etc", CONFIG_FILENAME)


class Config:
    """A base configuration object with some default settings."""

    config_filepaths = [DEFAULT_CONFIG_PATH]
    REGISTRATION = True

    def __init__(self, db_path=None):
        # Read parameters from the configuration files in order of specificity
        for config_filepath in filter(lambda p: p.exists(), self.config_filepaths):
            self._read_config_json(config_filepath)
        if db_path:
            self.DATABASE = db_path

    @property
    def DATABASE(self):
        return self._database

    @DATABASE.setter
    def DATABASE(self, value):
        # Ensure that the database path is always set as a `pathlib.Path` object
        self._database = Path(value)

    def _read_config_json(self, config_path):
        # Read keys and values from a configuration JSON
        with config_path.open() as config_json:
            config_mapping = json.load(config_json)
        for key, value in config_mapping.items():
            setattr(self, key, value)


class InstanceBasedConfig(Config):
    """A base configuration object for app modes using instance directories."""

    TESTING = False
    db_name = None

    @classmethod
    def configure_for_instance(cls, instance_path, **kwargs):
        """Instantiate the app based out of the given instance directory."""
        instance_path = Path(instance_path)
        instance_path.mkdir(parents=True, exist_ok=True)
        cls.config_filepaths = [
            *super().config_filepaths,
            instance_path / CONFIG_FILENAME,
        ]
        db_path = Path(instance_path, cls.db_name) if cls.db_name else None
        return cls(db_path=db_path, **kwargs)
