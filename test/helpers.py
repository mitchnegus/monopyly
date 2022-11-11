"""Helper objects to improve modularity of tests."""
import unittest

from sqlalchemy import inspect, select
from sqlalchemy.sql.expression import func

from monopyly.database import db


helper = unittest.TestCase()


class TestHandler:

    @classmethod
    def assertEntryMatch(cls, entry, reference):
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
        for entry, reference in zip(entries, references):
            cls.assertEntryMatch(entry, reference)

    @classmethod
    def assertContainEntry(cls, reference, entry):
        for value in reference:
            assert value in entry

    @classmethod
    def assertContainEntries(cls, reference, entries):
        for row, entry in zip(reference, entries):
            cls.assertContainEntry(row, entry)

    @classmethod
    def assertNumberOfMatches(cls, number, field, *criteria):
        query = select(func.count(field))
        if criteria:
            query = query.where(*criteria)
        count = db.session.execute(query).scalar()
        assert count == number


class TestGrouper:

    @staticmethod
    def compare_groupings(grouping, expected_id_groupings):
        for category_entry, entries in grouping.items():
            # Use IDs as a proxy for testing the full database query result
            category_id = category_entry['id']
            assert category_id in expected_id_groupings
            for entry in entries:
                assert entry['id'] in expected_id_groupings[category_id]

