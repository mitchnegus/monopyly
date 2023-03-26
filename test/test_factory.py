"""Tests for the application factory."""
from pathlib import Path
from unittest.mock import patch

from monopyly import create_app

# Rename config to avoid Pytest attempting to collect `TestingConfig`
from monopyly.config import DevelopmentConfig, ProductionConfig
from monopyly.config import TestingConfig as _TestingConfig


@patch("monopyly.database.SQLAlchemy.access_tables")
@patch("monopyly.Flask.debug", new=True)
def test_development_config(mock_access_method):
    app = create_app()
    assert app.config["SECRET_KEY"] == "development key"


@patch("monopyly.database.SQLAlchemy.access_tables")
@patch("monopyly.Path.exists")
def test_production_config(mock_exists_method, mock_access_method):
    mock_exists_method.return_value = True
    app = create_app()
    assert app.config["SECRET_KEY"] not in ["development key", "testing key"]
    # In production, the `access_tables` method should always be called
    mock_access_method.assert_called_once()


def test_test_config():
    assert not create_app().testing
    mock_db_path = "/path/to/test/db.sqlite"
    app = create_app(_TestingConfig(db_path=mock_db_path))
    assert app.testing
    assert app.config["SECRET_KEY"] == "testing key"
    assert app.config["DATABASE"] == Path(mock_db_path)
