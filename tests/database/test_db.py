"""Tests for the database."""
from unittest.mock import patch

from monopyly.database import back_up_db


def test_get_close_db(app):
    # Access the database
    with app.app_context():
        session = app.db.session
        assert session is app.db.session
    # Check that the session ended
    assert session is not app.db.session


def test_init_db_command_db_exists(runner, monkeypatch):
    # Create mock objects to test expected behavior
    class Recorder:
        called = False

    def mock_init_db(db, auxiliary_preload_path=None):
        Recorder.called = True

    monkeypatch.setattr("monopyly.database.SQLAlchemy.initialize", mock_init_db)
    result = runner.invoke(args=["init-db"])
    assert "Database exists" in result.output
    assert not Recorder.called


@patch("monopyly.config.default_settings.Path.is_file")
def test_init_db_command(mock_method, runner, monkeypatch):
    # Create mock objects to test expected behavior
    class Recorder:
        called = False

    def mock_init_db(db, auxiliary_preload_path):
        Recorder.called = True

    monkeypatch.setattr("monopyly.database.SQLAlchemy.initialize", mock_init_db)
    mock_method.return_value = False
    # Ensure that the database is initialized properly
    result = runner.invoke(args=["init-db"])
    assert "Initialized" in result.output
    assert Recorder.called


def test_back_up_db_command(runner, monkeypatch):
    # Create mock objects to test expected behavior
    class Recorder:
        called = False

    def mock_back_up_db(db, backup_db):
        Recorder.called = True

    monkeypatch.setattr("monopyly.database.back_up_db", mock_back_up_db)
    result = runner.invoke(args=["back-up-db"])
    assert "Backup complete" in result.output
    assert Recorder.called


@patch("sqlite3.Connection")
def test_back_up_db(mock_connection_type):
    db = mock_connection_type()
    backup_db = mock_connection_type()
    back_up_db(db, backup_db)
    db.backup.assert_called_once_with(backup_db)
    # The `close` method should be called twice, once for each database
    assert mock_connection_type.return_value.close.call_count == 2
