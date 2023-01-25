"""Helper objects to improve modularity of tests."""
import functools
import unittest

import pytest
from werkzeug.exceptions import NotFound
from sqlalchemy import inspect, select
from sqlalchemy.sql.expression import func
from bs4 import BeautifulSoup

from monopyly.database import db


helper = unittest.TestCase()


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

    @pytest.mark.usefixtures("_transaction_app_context")
    @functools.wraps(test_function)
    def wrapped_test_function(*args, **kwargs):
        test_function(*args, **kwargs)

    return wrapped_test_function


class TestHandler:

    @classmethod
    def assertEntryMatches(cls, entry, reference):
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

    @classmethod
    def assertNumberOfMatches(cls, number, field, *criteria):
        query = select(func.count(field))
        if criteria:
            query = query.where(*criteria)
        count = db.session.execute(query).scalar()
        assert count == number

    @classmethod
    def assert_invalid_user_entry_add_fails(cls, handler, mapping,
                                            invalid_user_id, invalid_matches):
        # Count the number of the entry type owned by the invalid user
        cls.assertNumberOfMatches(
            invalid_matches,
            handler.model.id,
            handler.model.id == invalid_user_id
        )
        # Ensure that the mapping cannot be added for the invalid user
        with pytest.raises(NotFound):
            handler.add_entry(**mapping)
        # Rollback and ensure the entry was not added for the invalid user
        db.session.close()
        cls.assertNumberOfMatches(
            invalid_matches,
            handler.model.id,
            handler.model.id == invalid_user_id
        )

    @classmethod
    def assert_entry_deletion_succeeds(cls, handler, entry_id):
        handler.delete_entry(entry_id)
        # Check that the entry was deleted
        cls.assertNumberOfMatches(
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

