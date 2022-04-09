"""Helper objects to improve modularity of tests."""
import unittest

from monopyly.db import get_db


class TestHandler:

    def assertMatchEntry(self, reference, entry):
        assert tuple(entry) == reference

    def assertMatchEntries(self, reference, entries):
        helper = unittest.TestCase()
        helper.assertCountEqual(map(tuple, entries), reference)

    def assertQueryEqualsCount(self, app, query, count):
        with app.app_context():
            db = get_db()
            db_count = db.execute(query).fetchone()[0]
            assert db_count == count
