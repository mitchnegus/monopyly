"""Tests for the database."""
import sqlite3

import pytest

from monopyly.db.db import get_db


def test_get_close_db(app):
    # Access the database
    with app.app_context():
        db = get_db()
        assert db is get_db()
    # Check that the database is closed (and is not returning values)
    with pytest.raises(sqlite3.ProgrammingError) as e:
        db.execute("SELECT 1")
    assert 'closed' in str(e.value)


def test_init_db_command(runner, monkeypatch):
    class Recorder:
        called = False

    def mock_init_db():
        Recorder.called = True

    monkeypatch.setattr('monopyly.db.init_db', mock_init_db)
    result = runner.invoke(args=['init-db'])
    assert 'Initialized' in result.output
    assert Recorder.called
