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


def populate_test_database(app):
    # Use a raw connection to the SQLite DBAPI to load entire files
    raw_conn = db.engine.raw_connection()
    raw_conn.executescript(TEST_DATA_SQL)
    raw_conn.close()
    # Access the tables with the database engine
    db.access_tables()


def provide_test_app(test_database_path):
    # Create a testing app
    app = create_app({
        'TESTING': True,
        'DATABASE': test_database_path
    })
    # Initialize the test database
    with app.app_context():
        init_db()
    populate_test_database(app)
    return app


@contextmanager
def testing_database_context():
    db_fd, db_path = tempfile.mkstemp()
    # Make sure that the database location is overwritten
    with patch('monopyly.database.DB_PATH', new=Path(db_path)):
        yield namedtuple('TemporaryFile', ['fd', 'path'])(db_fd, db_path)
    # After function execution, close the file and remove it
    os.close(db_fd)
    os.unlink(db_path)


# Build a test database, use it in an app, and then create a test client

@pytest.fixture(scope="session")
def app():
    with testing_database_context() as test_db:
        app = provide_test_app(test_db.path)
        yield app


@pytest.fixture
def client(app):
    yield app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


# Repeat the construction process, but now without session scoping to reset
# the database after a successful transaction

@pytest.fixture
def transaction_app():
    with testing_database_context() as test_db:
        # Generate an app object that persists for only one transaction
        app = provide_test_app(test_db.path)
        yield app


@pytest.fixture
def transaction_client(transaction_app):
    # Generate a client that persists for only one transaction
    yield transaction_app.test_client()


# Use the app/client for authorization

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


@pytest.fixture
def auth(client):
    return AuthActions(client)


@pytest.fixture
def client_context(client, auth):
    auth.login(username="mr.monopyly", password="MONOPYLY")
    with client:
        # Context variables (e.g. `g`) may be accessed only after response
        client.get('/')
        yield


@pytest.fixture
def user_table():
    return db.tables['users']

