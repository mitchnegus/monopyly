"""
Expose commonly used database functionality to the rest of the package.
"""
from pathlib import Path
from functools import wraps

import click
from flask import current_app, g
from flask.cli import with_appcontext
from sqlalchemy import create_engine, event, MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.schema import Table
from sqlalchemy.orm import sessionmaker, scoped_session

from ..definitions import INSTANCE_PATH
from .models import Model
from .schema import DATABASE_SCHEMA


DIALECT = 'sqlite'
DBAPI = 'pysqlite'
DB_NAME = 'monopyly.sqlite'
DB_PATH = Path(INSTANCE_PATH, DB_NAME)


class SQLAlchemy:
    """
    Store SQLAlchemy database objects.

    This is a wrapper for the `_SQLAlchemy` object. The wrapped object
    stores the database information and is the primary vehicle for
    interacting with the SQLAlchemy API. This object facilitates testing,
    to enable the state of that wrapped database object to be preserved
    over the course of many tests. (This is a major efficiency
    enhancement, as the database does not need to be recreated and/or
    repopulated for each test.
    """

    def __init__(self, *args, **kwargs):
        self.create(*args, **kwargs)

    def __getattr__(self, item):
        return getattr(self._db, item)

    def create(self, *args, **kwargs):
        self._db = _SQLAlchemy(*args, **kwargs)

    def save_state(self):
        return self._db

    def load_state(self, db):
        self._db = db


class _SQLAlchemy:
    """Store SQLAlchemy database objects."""
    _base = Model

    def __init__(self, db_path=None):
        self._path = db_path if db_path else DB_PATH
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

    def setup_engine(self, echo_engine=False):
        """Setup the database engine, a session factory, and metadata."""
        # Create the engine using the custom database URL
        db_url = f"{DIALECT}+{DBAPI}:///{self._path}"
        self.engine = create_engine(db_url, echo=echo_engine)
        # Use a session factory to generate sessions
        session_kwargs = {"bind": self.engine, "autoflush": False, "future": True}
        session_factory = sessionmaker(**session_kwargs)
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
        with db.session.begin():
            return func(*args, **kwargs)
    return wrapper


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo(f"Initialized the database ('{current_app.config['DATABASE']}')")


def init_db():
    """Execute the SQL schema to clear existing data and create new tables."""
    # Establish a raw connection in order to execute the complete files
    raw_conn = db.engine.raw_connection()
    # Load the tables, table views, and preloaded data
    sql_dir = Path(__file__).parent
    sql_filenames = ("schema.sql", "views.sql", "preloads.sql")
    for filename in sql_filenames:
        sql_filepath = sql_dir / filename
        with current_app.open_resource(sql_filepath) as sql_file:
            raw_conn.executescript(sql_file.read().decode('utf8'))
    raw_conn.close()
    # Register tables with the SQLAlchemy metadata
    db.metadata.create_all(bind=db.engine)


def close_db(exception=None):
    """Close the database if it is open."""
    if db.scoped_session is not None:
        db.scoped_session.remove()

