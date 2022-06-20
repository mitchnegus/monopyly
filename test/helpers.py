"""Helper objects to improve modularity of tests."""
import unittest

from monopyly.db import get_db


helper = unittest.TestCase()


class TestHandler:

    @classmethod
    def assertMatchEntry(cls, reference, entry):
        assert tuple(entry) == reference

    @classmethod
    def assertMatchEntries(cls, reference, entries, order=False):
        if order:
            for row, entry in zip(reference, entries):
                cls.assertMatchEntry(row, entry)
        else:
            helper.assertCountEqual(map(tuple, entries), reference)

    @classmethod
    def assertContainEntry(cls, reference, entry):
        for value in reference:
            assert value in entry

    @classmethod
    def assertContainEntries(cls, reference, entries):
        for row, entry in zip(reference, entries):
            cls.assertContainEntry(row, entry)

    @classmethod
    def assertQueryEqualsCount(cls, app, query, count):
        with app.app_context():
            db = get_db()
            db_count = db.execute(query).fetchone()[0]
            assert db_count == count


class TestGrouper:

    @staticmethod
    def compare_groupings(grouping, expected_id_groupings):
        for category_entry, entries in grouping.items():
            # Use IDs as a proxy for testing the full database query result
            category_id = category_entry['id']
            assert category_id in expected_id_groupings
            for entry in entries:
                assert entry['id'] in expected_id_groupings[category_id]

