"""Tests for the database."""
from unittest.mock import patch


def test_get_close_db(app):
    # Access the database
    with app.app_context():
        session = app.db.session
        assert session is app.db.session
    # Check that the session ended
    assert session is not app.db.session


def test_init_db_command_db_exists(runner, monkeypatch):
    class Recorder:
        called = False

    def mock_init_db():
        Recorder.called = True

    monkeypatch.setattr('monopyly.database.init_db', mock_init_db)
    result = runner.invoke(args=['init-db'])
    assert 'Database exists' in result.output
    assert not Recorder.called


@patch("monopyly.config.default_settings.Path.is_file")
def test_init_db_command(mock_method, runner, monkeypatch):
    # Create mock objects to test expected behavior
    class Recorder:
        called = False

    def mock_init_db(db):
        Recorder.called = True

    monkeypatch.setattr('monopyly.database.init_db', mock_init_db)
    mock_method.return_value = False
    # Ensure that the database is initialized properly
    result = runner.invoke(args=['init-db'])
    assert 'Initialized' in result.output
    assert Recorder.called

