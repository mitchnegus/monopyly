"""
Expose commonly used database functionality to the rest of the package.
"""
import sqlite3
from functools import wraps
from pathlib import Path

import click
from flask import current_app, g
from flask.cli import with_appcontext
from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.schema import Table

from ..core.actions import get_timestamp
from .models import Model
from .schema import DATABASE_SCHEMA

DIALECT = "sqlite"
DBAPI = "pysqlite"
DB_NAME = "monopyly.sqlite"


class SQLAlchemy:
    """Store SQLAlchemy database objects."""

    _base = Model

    def __init__(self, db_path=None):
        self.engine = None
        self.metadata = None
        self.scoped_session = None

    @property
    def tables(self):
        return self.metadata.tables

    @property
    def session(self):
        # Returns the current `Session` object
        return self.scoped_session()

    def setup_engine(self, db_path, echo_engine=False):
        """Setup the database engine, a session factory, and metadata."""
        # Create the engine using the custom database URL
        db_url = f"{DIALECT}+{DBAPI}:///{db_path}"
        self.engine = create_engine(db_url, echo=echo_engine)
        # Use a session factory to generate sessions
        session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            future=True,
        )
        self.scoped_session = scoped_session(session_factory)
        self._base.query = self.scoped_session.query_property()
        # Add metadata
        self.metadata = MetaData()

    def access_tables(self):
        for table_name in DATABASE_SCHEMA.keys():
            Table(table_name, self.metadata, autoload_with=self.engine)


db = SQLAlchemy()


def db_transaction(func):
    """A decorator denoting the wrapped function as a database transaction."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        with current_app.db.session.begin():
            return func(*args, **kwargs)

    return wrapper


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Initialize the database from the command line (if it does not exist)."""
    db_path = current_app.config["DATABASE"]
    if not db_path.is_file():
        preload_path = current_app.config.get("PRELOAD_DATA_PATH")
        init_db(current_app.db, preload_path)
        click.echo(f"Initialized the database ('{db_path}')")
        if preload_path:
            click.echo(f"Prepopulated the database using '{preload_path}'")
    else:
        click.echo(f"Database exists, using '{db_path}'")


def init_db(db, auxiliary_preload_path=None):
    """Execute the SQL schema to clear existing data and create new tables."""
    # Establish a raw connection in order to execute the complete files
    raw_conn = db.engine.raw_connection()
    # Load the tables, table views, and preloaded data
    sql_dir = Path(__file__).parent
    sql_filepaths = [
        sql_dir / path for path in ("schema.sql", "views.sql", "preloads.sql")
    ]
    if auxiliary_preload_path:
        sql_filepaths.append(auxiliary_preload_path)
    for sql_filepath in sql_filepaths:
        with current_app.open_resource(sql_filepath) as sql_file:
            raw_conn.executescript(sql_file.read().decode("utf8"))
    raw_conn.close()
    # Register tables with the SQLAlchemy metadata
    db.metadata.create_all(bind=db.engine)


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


def close_db(exception=None):
    """Close the database if it is open."""
    if current_app.db.scoped_session is not None:
        current_app.db.scoped_session.remove()
