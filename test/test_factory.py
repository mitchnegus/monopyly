"""Tests for the application factory."""
from unittest.mock import patch

from monopyly import create_app
# Rename config to avoid Pytest attempting to collect `TestingConfig`
from monopyly.config import (
    DevelopmentConfig,
    ProductionConfig,
    TestingConfig as _TestingConfig
)


@patch("monopyly.Flask.debug", new=True)
def test_development_config():
    app = create_app()
    assert app.config["SECRET_KEY"] == "development key"


def test_production_config():
    app = create_app()
    assert app.config["SECRET_KEY"] not in ["development key", "testing key"]


def test_test_config():
    assert not create_app().testing
    app = create_app(_TestingConfig)
    assert app.testing
    assert app.config["SECRET_KEY"] == "testing key"

