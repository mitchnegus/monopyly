"""
Expose commonly used database functionality to the rest of the package.
"""

import sqlite3
from pathlib import Path

import click
from flask import current_app
from flask.cli import with_appcontext
from fuisce.database import SQLAlchemy as _SQLAlchemy

from ..cli.console import echo_text
from ..core.actions import get_timestamp

BASE_DB_NAME = f"monopyly.sqlite"


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


SQLAlchemy.create_default_interface(echo_engine=False)


@click.command("init-db")
def init_db_command():
    """Initialize the database from the command line (if it does not already exist)."""
    init_db()


@with_appcontext
def init_db():
    """Initialize the database (if it does not already exist)."""
    db_path = current_app.config["DATABASE"]
    echo_db_info("Initializing the database...")
    if not db_path.is_file():
        current_app.db.initialize(current_app)
        echo_db_info(f"Initialized the database ('{db_path}')")
        preload_path = current_app.config.get("PRELOAD_DATA_PATH")
        if preload_path:
            echo_db_info(f"Prepopulated the database using '{preload_path}'")
    else:
        echo_db_info(f"Database exists, using '{db_path}'")


@click.command("back-up-db")
def back_up_db_command():
    """Back up the database from the command line."""
    back_up_db()


@with_appcontext
def back_up_db():
    """Create a backup of the database."""
    echo_db_info("Backing up the database...")
    timestamp = get_timestamp()
    # Connect to the databases and back it up
    db = sqlite3.connect(current_app.config["DATABASE"])
    with (backup_db := _connect_to_backup_database(current_app, timestamp)):
        db.backup(backup_db)
    # Close the connections
    backup_db.close()
    db.close()
    echo_db_info(f"Backup complete ({timestamp})")


def _connect_to_backup_database(current_app, timestamp):
    backup_db_dir_path = Path(current_app.instance_path) / "db_backups"
    # Create the directory if it does not already exist
    backup_db_dir_path.mkdir(exist_ok=True, parents=True)
    # Connect to (and create) the backup directory with proper timestamp
    backup_db_path = backup_db_dir_path / f"backup_{timestamp}.sqlite"
    backup_db = sqlite3.connect(backup_db_path)
    return backup_db


def register_db_cli_commands(app):
    """Register database CLI commands with the app."""
    app.cli.add_command(init_db_command)
    app.cli.add_command(back_up_db_command)


def echo_db_info(text):
    """Echo text to the terminal for database-related information."""
    echo_text(text, color="deep_sky_blue1")
