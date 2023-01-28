"""Default configuration settings."""
from pathlib import Path

from ..database import DB_NAME


class Config:
    """A base configuration object with some default settings."""
    TESTING = False

    def __init__(self):
        self._database = None

    @property
    def DATABASE(self):
        return self._database

    @DATABASE.setter
    def DATABASE(self, value):
        # Ensure that the database path is set as a `pathlib.Path` object
        self._database = Path(value)

