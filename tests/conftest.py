import os
import tempfile

import pytest
from monopyly import create_app
from monopyly.db import get_db, init_db


with open(os.path.join(os.path.dirname(__file__), 'data.sql'), 'rb') as f:
    _data_sql = f.read().decode('utf-8')


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    # Create a testing app
    app = create_app({
        'TESTING': True,
        'DATABASE': db_path
    })
    # Initialize the test database
    with app.app_context():
        init_db()
        get_db().execute_script(_data_sql)

    yield app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()
