"""
Expose commonly used database functionality to the rest of the package.
"""
import sqlite3
from functools import wraps
from pathlib import Path

import click
from authanor.database import SQLAlchemy as _SQLAlchemy
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy.schema import Table

from ..core.actions import get_timestamp

DB_NAME = "monopyly.sqlite"


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
            auxiliary_preload_path = app.config["PRELOAD_DATA_PATH"]
            if auxiliary_preload_path:
                sql_filepaths.append(auxiliary_preload_path)
            for sql_filepath in sql_filepaths:
                with current_app.open_resource(sql_filepath) as sql_file:
                    raw_conn.executescript(sql_file.read().decode("utf8"))
            raw_conn.close()
        super().initialize(app)


db = SQLAlchemy()


def db_transaction(func):
    """A decorator denoting the wrapped function as a database transaction."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        with current_app.db.session.begin():
            return func(*args, **kwargs)

    return wrapper


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Initialize the database from the command line (if it does not exist)."""
    db_path = current_app.config["DATABASE"]
    if not db_path.is_file():
        preload_path = current_app.config.get("PRELOAD_DATA_PATH")
        current_app.db.initialize(current_app)
        click.echo(f"Initialized the database ('{db_path}')")
        if preload_path:
            click.echo(f"Prepopulated the database using '{preload_path}'")
    else:
        click.echo(f"Database exists, using '{db_path}'")


@click.command("back-up-db")
@with_appcontext
def back_up_db_command():
    """Back up the database from the command line."""
    timestamp = get_timestamp()
    # Connect to the database
    db = sqlite3.connect(current_app.config["DATABASE"])
    # Create and connect to the backup database
    backup_db_dir_path = Path(current_app.instance_path) / "db_backups"
    backup_db_dir_path.mkdir(exist_ok=True, parents=True)
    backup_db_path = backup_db_dir_path / f"backup_{timestamp}.sqlite"
    backup_db = sqlite3.connect(backup_db_path)
    # Back up the database and print status
    back_up_db(db, backup_db)
    click.echo(f"Backup complete ({timestamp})")


def back_up_db(db, backup_db):
    """Create a backup of the database."""
    # Backup the database
    with backup_db:
        db.backup(backup_db)
    # Close the connections
    backup_db.close()
    db.close()
