"""Helper objects to improve modularity of tests."""
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

