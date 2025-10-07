"""
Expose commonly used database functionality to the rest of the package.
"""

from pathlib import Path

from dry_foundation.database import SQLAlchemy as _SQLAlchemy
from flask import current_app


class SQLAlchemy(_SQLAlchemy):
    """Store an interface to SQLAlchemy database objects."""

    def initialize(self, app):
        """
        Initialize the database.

        Initialize the database by executing the SQL schema to clear
        existing data and create new tables.

        Parameters
        ----------
        app : flask.Flask
            The app object, which may pass initialization parameters via
            its configuration.
        """
        with app.app_context():
            # Establish a raw connection in order to execute the complete files
            raw_conn = self.engine.raw_connection()
            # Load the tables, table views, and preloaded data
            sql_dir = Path(__file__).parent
            sql_filepaths = [
                sql_dir / path for path in ("schema.sql", "views.sql", "preloads.sql")
            ]
            auxiliary_preload_path = app.config.get("PRELOAD_DATA_PATH")
            if auxiliary_preload_path:
                sql_filepaths.append(auxiliary_preload_path)
            for sql_filepath in sql_filepaths:
                with current_app.open_resource(sql_filepath) as sql_file:
                    raw_conn.executescript(sql_file.read().decode("utf8"))
            raw_conn.close()
        # Top level initialization does not overwrite tables, so it goes at the end
        super().initialize(app)
