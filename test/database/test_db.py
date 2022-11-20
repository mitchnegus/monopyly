"""Tests for the database."""
from monopyly.database import db


def test_get_close_db(app):
    # Access the database
    with app.app_context():
        session = db.session
        assert session is db.session
    # Check that the session ended
    assert session is not db.session


def test_init_db_command(runner, monkeypatch):
    class Recorder:
        called = False

    def mock_init_db():
        Recorder.called = True

    monkeypatch.setattr('monopyly.database.init_db', mock_init_db)
    result = runner.invoke(args=['init-db'])
    assert 'Initialized' in result.output
    assert Recorder.called

