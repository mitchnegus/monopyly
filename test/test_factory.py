"""Tests for the application factory."""
from unittest.mock import patch

from monopyly import create_app

# Rename config to avoid Pytest attempting to collect `TestingConfig`
from monopyly.config import DevelopmentConfig, ProductionConfig
from monopyly.config import TestingConfig as _TestingConfig


@patch("monopyly.Flask.debug", new=True)
def test_development_config():
    app = create_app()
    assert app.config["SECRET_KEY"] == "development key"


@patch("monopyly.database.SQLAlchemy.access_tables")
@patch("monopyly.Path.exists")
def test_production_config(mock_exists_method, mock_access_method):
    mock_exists_method.return_value = True
    app = create_app()
    assert app.config["SECRET_KEY"] not in ["development key", "testing key"]
    mock_access_method.assert_called_once()


def test_test_config():
    assert not create_app().testing
    app = create_app(_TestingConfig)
    assert app.testing
    assert app.config["SECRET_KEY"] == "testing key"
