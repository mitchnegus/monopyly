from pathlib import Path

import pytest
from dry_foundation.testing import AppTestManager

import monopyly

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
    import_name=monopyly.__name__,
    factory=monopyly.create_app,
    preload_data_path=PRELOAD_DATA_PATH,
)


@pytest.fixture
def app():
    return app_manager.get_app()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth(client):
    return AuthActions(client)


@pytest.fixture
def authorization(auth):
    auth.login(username="mr.monopyly", password="MONOPYLY")
    return


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
