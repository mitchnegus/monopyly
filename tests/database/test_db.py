"""Tests for the database."""

from unittest.mock import Mock, patch

from flask import current_app

from monopyly.database import back_up_db


def test_get_close_db(app):
    # Access the database
    with app.app_context():
        session = app.db.session
        assert session is app.db.session
    # Check that the session ended
    assert session is not app.db.session


@patch("monopyly.config.default_settings.Path.is_file", new=Mock(return_value=True))
def test_init_db_command_db_exists(runner):
    result = runner.invoke(args=["init-db"])
    assert "Database exists" in result.output


@patch("monopyly.config.default_settings.Path.is_file", new=Mock(return_value=False))
@patch("monopyly.database.SQLAlchemy.initialize")
def test_init_db_command(mock_init_db, app, runner):
    result = runner.invoke(args=["init-db"])
    assert "Initialized" in result.output
    mock_init_db.assert_called_once()


@patch("sqlite3.connect")
def test_back_up_db_command(mock_connect_method, runner):
    db = mock_connect_method.return_value
    backup_db = mock_connect_method.return_value
    result = runner.invoke(args=["back-up-db"])
    assert "Backup complete" in result.output
    db.backup.assert_called_once_with(backup_db)
    # The `close` method should be called twice, once for each database
    assert mock_connect_method.return_value.close.call_count == 2
