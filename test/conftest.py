import pytest

from .helpers import AppManager


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


def pytest_generate_tests(metafunc):
    """
    Control test generation.

    This function overrides the built-in Pytest function to explicitly
    control test generation. Here, controlling test generation is
    required to alter the order of the `metafunc.fixturenames`
    attribute. The fixtures defined in that list are called (in order)
    when setting up a test function; however, for this app's tests to
    perform optimally, the `transaction_app_context` must be the very
    first fixture called so that the proper testing context is used.
    """
    priority_fixture = "transaction_app_context"
    if priority_fixture in metafunc.fixturenames:
        metafunc.fixturenames.remove(priority_fixture)
        metafunc.fixturenames.insert(0, priority_fixture)


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
        # Context variables (e.g., `g`) may be accessed only after response
        client.get('/')
        yield


# Streamline access to the database user table

@pytest.fixture
def user_table(app):
    return app.db.tables['users']

