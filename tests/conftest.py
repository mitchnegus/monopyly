from pathlib import Path

import pytest
from fuisce.testing import AppTestManager

from monopyly import create_app
from monopyly.config import TestingConfig

TEST_DIR = Path(__file__).parent
PRELOAD_DATA_PATH = TEST_DIR / "data.sql"


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


# Instantiate the app manager to determine the correct app (persistent/ephemeral)
app_manager = AppTestManager(
    factory=create_app, config=TestingConfig, preload_data_path=PRELOAD_DATA_PATH
)


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
