"""Helper objects to improve modularity of tests."""
import os
import functools
import tempfile
import unittest
from pathlib import Path
from collections import namedtuple
from contextlib import contextmanager

import pytest
from werkzeug.exceptions import NotFound
from sqlalchemy import inspect, select
from sqlalchemy.sql.expression import func
from bs4 import BeautifulSoup

from monopyly import create_app
from monopyly.config import TestingConfig
from monopyly.database import init_db


TEST_DIR = Path(__file__).parent

helper = unittest.TestCase()


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
            app = cls.ephemeral_app
        else:
            app = cls.persistent_app
        return app

    @classmethod
    def _generate_app(cls, test_database_path):
        # Create a testing app
        test_config = TestingConfig(db_path=test_database_path)
        app = create_app(test_config)
        return app

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
            app = cls._generate_app(test_db.path)
            cls._setup_test_database(app)
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

    @classmethod
    def _setup_test_database(cls, app):
        """Initialize the test database and populate it with test data."""
        with app.app_context():
            init_db(app.db)
            cls._populate_test_database(app.db)

    @staticmethod
    def _populate_test_database(db):
        """
        Use a raw connection to the SQLite DBAPI to load entire files

        Establish a raw connection to the database and use it to populate
        the database tables with the preloaded test data.
        """
        # Load the SQLite instructions adding the preloaded testing data
        with Path(TEST_DIR, "data.sql").open("rb") as test_data_sql_file:
            test_data_sql = test_data_sql_file.read().decode('utf-8')
        # Connect to the database, and add the preloaded test data
        raw_conn = db.engine.raw_connection()
        raw_conn.executescript(test_data_sql)
        raw_conn.close()
        # Once loaded, access the tables with the database engine
        db.access_tables()


def transaction_lifetime(test_function):
    """
    Create a decorator to leverage an ephemeral app.

    While many tests just check elements in the database, and so can
    share a persistent app object for performance reasons. However, some
    transactions must update (and commit to) the database to be
    successful. For these cases, this decorator provides access to an
    app object with a lifetime of only this one transaction. That new
    app is entirely separate from the persistent app, and so generates
    an entirely new instance of the test database that exists only for
    the lifetime of the test being decorated.

    Parameters
    ----------
    test_function : callable
        The test function to be decorated which will use a new app with
        a lifetime of just this test (one database transaction).

    Returns
    -------
    wrapped_test_function : callable
        The wrapped test.
    """

    @pytest.mark.usefixtures("transaction_app_context")
    @functools.wraps(test_function)
    def wrapped_test_function(*args, **kwargs):
        test_function(*args, **kwargs)

    return wrapped_test_function


class TestHandler:

    @pytest.fixture(autouse=True)
    def _get_app(self, app):
        # Use the client fixture in route tests
        self._app = app

    @staticmethod
    def assertEntryMatches(entry, reference):
        assert isinstance(entry, type(reference))
        for column in inspect(type(entry)).columns:
            field = column.name
            assert getattr(entry, field) == getattr(reference, field)

    @classmethod
    def assertEntriesMatch(cls, entries, references, order=False):
        if not order:
            # Order does not matter, so sort both entries and references by ID
            entries = sorted(entries, key=lambda entry: entry.id)
            references = sorted(references, key=lambda reference: reference.id)
        else:
            # Convert the items to lists to ensure they are the same length
            entries = list(entries)
            references = list(references)
        assert len(entries) == len(references)
        # Compare the list elements
        for entry, reference in zip(entries, references):
            cls.assertEntryMatches(entry, reference)

    def assertNumberOfMatches(self, number, field, *criteria):
        query = select(func.count(field))
        if criteria:
            query = query.where(*criteria)
        count = self._app.db.session.execute(query).scalar()
        assert count == number

    def assert_invalid_user_entry_add_fails(self, handler, mapping,
                                            invalid_user_id, invalid_matches):
        # Count the number of the entry type owned by the invalid user
        self.assertNumberOfMatches(
            invalid_matches,
            handler.model.id,
            handler.model.id == invalid_user_id
        )
        # Ensure that the mapping cannot be added for the invalid user
        with pytest.raises(NotFound):
            handler.add_entry(**mapping)
        # Rollback and ensure the entry was not added for the invalid user
        self._app.db.session.close()
        self.assertNumberOfMatches(
            invalid_matches,
            handler.model.id,
            handler.model.id == invalid_user_id
        )

    def assert_entry_deletion_succeeds(self, handler, entry_id):
        handler.delete_entry(entry_id)
        # Check that the entry was deleted
        self.assertNumberOfMatches(
            0, handler.model.id, handler.model.id == entry_id
        )


class TestRoutes:

    blueprint_prefix = None

    @property
    def client(self):
        return self._client

    @pytest.fixture(autouse=True)
    def _get_client(self, client):
        # Use the client fixture in route tests
        self._client = client

    def route_loader(method):
        # Load the route accounting for the blueprint
        @functools.wraps(method)
        def wrapper(self, route, *args, **kwargs):
            if self.blueprint_prefix is not None:
                route =  f"/{self.blueprint_prefix}{route}"
            method(self, route, *args, **kwargs)
            # Save the response as HTML
            self.html = self.response.data.decode("utf-8")
            self.soup = BeautifulSoup(self.html, "html.parser")
        return wrapper

    @route_loader
    def get_route(self, route, *args, **kwargs):
        """Load the HTML returned by accessing the route (via 'GET')."""
        self.response = self.client.get(route, *args, **kwargs)

    @route_loader
    def post_route(self, route, *args, **kwargs):
        """Load the HTML returned by accessing the route (via 'POST')."""
        self.response = self.client.post(route, *args, **kwargs)

