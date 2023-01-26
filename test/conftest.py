import os
import tempfile
from collections import namedtuple
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from flask import g
from sqlalchemy.orm import Session

from monopyly import create_app
from monopyly.database import db, init_db


TEST_DIR = Path(__file__).parent


# Load the SQLite instructions adding the preloaded testing data
with Path(TEST_DIR, "data.sql").open("rb") as test_data_preload_file:
    TEST_DATA_SQL = test_data_preload_file.read().decode('utf-8')


def provide_test_app(test_database_path):
    """
    Provide a Flask application configured for testing.

    Create a Flask application configured for testing that points to the
    test database. Given the path to the test database (ideally a
    temporary file), the database is initialized for the newly created
    app. The `SQLAlchemy` reference object (`monopyly.database.db`) is
    used to save the "state" of the database (e.g., the engine,
    metadata, tables, etc.) to the app object. This allows the global
    database reference to be updated for tests that should use a fresh
    copy of the database, and then restore this database state to the
    global variable when returning to use a previously created version.
    """
    # Create a new database object for testing
    db.create(db_path=test_database_path)
    # Create a testing app
    app = create_app({
        'TESTING': True,
        'DATABASE': test_database_path,
        'WTF_CSRF_ENABLED': False,
    })
    # Initialize the test database
    with app.app_context():
        init_db()
        app._db = db.save_state()
    populate_test_database(app)
    return app


def populate_test_database(app):
    """
    Use a raw connection to the SQLite DBAPI to load entire files

    Establish a raw connection to the database and use it to populate
    the database tables with the preloaded test data.
    """
    raw_conn = db.engine.raw_connection()
    raw_conn.executescript(TEST_DATA_SQL)
    raw_conn.close()
    # Once loaded, access the tables with the database engine
    db.access_tables()


class AppManager:
    """
    An object for managing apps during testing.

    Flask tests require access to an app, and this app provides access
    to the database. To avoid recreating the database on every test (and
    thus substantially improve test performance times), it is convenient
    to persist the app and database throughout the duration of testing.
    However, tests that consist of complete SQLAlchemy transactions
    which alter the database (e.g., additions, updates, deletions;
    operations that include a commit) would change this persistent
    database version and impact subsequent tests. Since simply rolling
    back the changes is insufficient to restore the database, this
    object manages which app (and database) are used for a transaction.
    The current app options are either
        (1) A persistent app, which survives through the entire test
            process and provides quick database access; or
        (2) An ephemeral app, which is designed to survive through only
            one single test.

    To enable switching between the two types of apps, this class relies
    two Pytest fixtures (`app_context` and `transaction_app_contex`) to
    control the scope of the two apps. The `app_context` fixture is
    created just once for the session and is then automatically used in
    all tests. On the other hand, the `transaction_app_context` fixture
    may be manually included in any test, which causes an ephemeral app
    to be created (and then used) only for that one test. To avoid
    cluttering test signatures, the `transaction_lifetime` decorator
    helper is provided to signal that a test should use the ephemeral
    app rather than calling the `transaction_app_context` fixture
    directly.
    """

    persistent_app = None
    ephemeral_app = None

    @classmethod
    def get_app(cls):
        if cls.ephemeral_app:
            return cls.ephemeral_app
        db.load_state(cls.persistent_app._db)
        return cls.persistent_app

    @classmethod
    def generate_app(cls, test_db_path):
        return provide_test_app(test_db_path)

    @classmethod
    def persistent_context(cls):
        return cls._app_test_context("persistent_app")

    @classmethod
    def ephemeral_context(cls):
        return cls._app_test_context("ephemeral_app")

    @classmethod
    @contextmanager
    def _app_test_context(cls, app_name):
        """
        Create a testing context for an app.

        Given the app name (either "ephemeral_app" or "persistent_app"),
        this context manager defines a context for that app, including
        the creation of a temporary database to be used by that version
        of the test app. Multiple test contexts may be generated and
        associated with the `AppManager` to enable access to different
        apps depending on the test.
        """
        with cls._database_test_context() as test_db:
            app = cls.generate_app(test_db.path)
            setattr(cls, app_name,  app)
            yield
            setattr(cls, app_name, None)

    @staticmethod
    @contextmanager
    def _database_test_context():
        """
        Create a temporary file for the database.

        This context manager creates a temporary file that is used for the
        testing database. The temporary file persists as long as the context
        survives, and the temporarykjj file is removed after the context
        lifetime is completed.
        """
        db_fd, db_path = tempfile.mkstemp()
        yield namedtuple('TemporaryFile', ['fd', 'path'])(db_fd, db_path)
        # After function execution, close the file and remove it
        os.close(db_fd)
        os.unlink(db_path)


# Use an app/client for authorization

class AuthActions:

    def __init__(self, client):
        self._client = client

    def login(self, username='test', password='test'):
        return self._client.post(
            '/auth/login',
            data={'username': username, 'password': password}
        )

    def logout(self):
        return self._client.get('/auth/logout')


# Build a test database, use it in an app, and then create a test client

@pytest.fixture(scope="session", autouse=True)
def app_context():
    with AppManager.persistent_context():
        yield

@pytest.fixture
def transaction_app_context():
    with AppManager.ephemeral_context():
        yield


@pytest.fixture
def app():
    yield AppManager.get_app()


@pytest.fixture
def client(app):
    yield app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def auth(client):
    return AuthActions(client)


@pytest.fixture
def authorization(auth):
    auth.login(username="mr.monopyly", password="MONOPYLY")
    yield


@pytest.fixture
def client_context(client, authorization):
    with client:
        # Context variables (e.g. `g`) may be accessed only after response
        client.get('/')
        yield


# Streamline access to the database user table

@pytest.fixture
def user_table():
    return db.tables['users']

