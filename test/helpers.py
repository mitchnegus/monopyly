"""Helper objects to improve modularity of tests."""
import unittest

from monopyly.db import get_db


class TestHandler:

    def assertMatchEntry(self, reference, entry):
        assert tuple(entry) == reference

    def assertMatchEntries(self, reference, entries, order=False):
        helper = unittest.TestCase()
        if order:
            for row, entry in zip(reference, entries):
                self.assertMatchEntry(row, entry)
        else:
            helper.assertCountEqual(map(tuple, entries), reference)

    def assertContainEntry(self, reference, entry):
        for value in reference:
            assert value in entry

    def assertContainEntries(self, reference, entries):
        for row, entry in zip(reference, entries):
            self.assertContainEntry(row, entry)

    def assertQueryEqualsCount(self, app, query, count):
        with app.app_context():
            db = get_db()
            db_count = db.execute(query).fetchone()[0]
            assert db_count == count
