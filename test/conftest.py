import os
import tempfile
from collections import namedtuple
from pathlib import Path
from unittest.mock import patch

import pytest

from monopyly import create_app
from monopyly.database import db, init_db


with open(os.path.join(os.path.dirname(__file__), 'data.sql'), 'rb') as f:
    _data_sql = f.read().decode('utf-8')


@pytest.fixture(autouse=True)
def temporary_database():
    db_fd, db_path = tempfile.mkstemp()
    # Make sure that the database location is overwritten
    with patch('monopyly.database.DB_PATH', new=Path(db_path)):
        yield namedtuple('TemporaryFile', ['fd', 'path'])(db_fd, db_path)
    # After function execution, close the file and remove it
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def app(temporary_database):
    # Create a testing app
    app = create_app({
        'TESTING': True,
        'DATABASE': temporary_database.path
    })
    # Initialize the test database
    with app.app_context():
        init_db()
        # Use a raw connection to the SQLite DBAPI to load entire files
        raw_conn = db.engine.raw_connection()
        raw_conn.executescript(_data_sql)
        raw_conn.close()
        # TEMP?: Access tables (again, would have failed during app initialization)
        db.access_tables()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


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
def client_context(app, client, auth):
    auth.login('mr.monopyly', 'MONOPYLY')
    with client:
        # Context variables (e.g. `g`) may be accessed only after response
        client.get('/')
        yield client_context


@pytest.fixture
def user_table():
    return db.tables['users']

