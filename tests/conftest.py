from contextlib import contextmanager
from pathlib import Path

import pytest
from authanor.testing.helpers import AppTestManager

from monopyly import create_app
from monopyly.config import TestingConfig

TEST_DIR = Path(__file__).parent


class AuthActions:
    """An object for performing authorized actions on behalf of a client."""

    def __init__(self, client):
        self._client = client

    def login(self, username="test", password="test"):
        return self._client.post(
            "/auth/login", data={"username": username, "password": password}
        )

    def logout(self):
        return self._client.get("/auth/logout")


class AppManager(AppTestManager):
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
    on two Pytest fixtures (`app_context` and `app_transaction_context`)
    to control the scope of the two apps. The `app_context` fixture is
    created just once for the session and is then automatically used in
    all tests. On the other hand, the `app_transaction_context` fixture
    may be manually included in any test, which causes an ephemeral app
    to be created (and then used) only for that one test. To avoid
    cluttering test signatures, the `transaction_lifetime` decorator
    helper is provided to signal that a test should use the ephemeral
    app rather than calling the `app_transaction_context` fixture
    directly.
    """

    @staticmethod
    def prepare_test_config(test_database_path):
        """Prepare the test configuration object."""
        preload_data_path = TEST_DIR / "data.sql"
        test_config = TestingConfig(
            db_path=test_database_path,
            preload_data_path=preload_data_path,
        )
        return test_config


# Instantiate the app manager to determine the correct app (persistent/ephemeral)
app_manager = AppManager(factory=create_app)


@pytest.fixture
def app():
    yield app_manager.get_app()


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
        # Context variables (e.g., `g`) may be accessed only after response
        client.get("/")
        yield


# Streamline access to the database user table


@pytest.fixture
def user_table(app):
    return app.db.tables["users"]
