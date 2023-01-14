"""Helper objects to improve modularity of tests."""
import functools
import unittest

import pytest
from werkzeug.exceptions import NotFound
from sqlalchemy import inspect, select
from sqlalchemy.sql.expression import func

from monopyly.database import db


helper = unittest.TestCase()


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

    _client = None
    _transaction_client = None
    blueprint_prefix = None

    @property
    def client(self):
        if self._transaction_client:
            return self._transaction_client
        return self._client

    @pytest.fixture(autouse=True)
    def _get_client(self, client):
        # Get a client object that will persist for all tests
        self._client = client
        yield
        # Reset the client on teardown
        self._client = None

    @pytest.fixture
    def _get_transaction_client(self, transaction_client):
        # Get a transaction client that will persist for only the current test
        self._transaction_client = transaction_client
        yield
        # Reset the transaction client on teardown
        self._transaction_client = None

    def transaction_client_lifetime(test_method):
        # Decorate methods to use the transaction client instead of the
        # standard client (the client will persist for only the current test)
        @pytest.mark.usefixtures("_get_transaction_client")
        @functools.wraps(test_method)
        def wrapper(self, *args, **kwargs):
            test_method(self, *args, **kwargs)
        return wrapper

    def route_loader(method):
        # Load the route accounting for the blueprint
        @functools.wraps(method)
        def wrapper(self, route, *args, **kwargs):
            if self.blueprint_prefix is not None:
                route =  f"/{self.blueprint_prefix}{route}"
            method(self, route, *args, **kwargs)
            # Save the response as HTML
            self.html = self.response.data.decode("utf-8")
        return wrapper

    @route_loader
    def get_route(self, route, *args, **kwargs):
        """Load the HTML returned by accessing the route (via 'GET')."""
        self.response = self.client.get(route, *args, **kwargs)

    @route_loader
    def post_route(self, route, *args, **kwargs):
        """Load the HTML returned by accessing the route (via 'POST')."""
        self.response = self.client.post(route, *args, **kwargs)

