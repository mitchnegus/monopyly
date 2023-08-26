"""Tests for the application factory."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

# Rename testing config to avoid Pytest attempting to collect `TestingConfig`
from monopyly import create_app
from monopyly.config import ProductionConfig
from monopyly.config import TestingConfig as _TestingConfig


@pytest.fixture
def default_config_file(tmp_path):
    config_filepath = tmp_path / "monopyly-config.json"
    with config_filepath.open("w") as test_config_file:
        json.dump({"SECRET_KEY": "test secret key", "OTHER": "other"}, test_config_file)
    return config_filepath


@pytest.fixture
def instance_path(tmp_path):
    instance_dir = tmp_path / "instance"
    instance_dir.mkdir()
    yield instance_dir


@pytest.fixture
def instance_config_file(instance_path):
    config_filepath = instance_path / "monopyly-config.json"
    with config_filepath.open("w") as test_config_file:
        json.dump({"OTHER": "test supersede"}, test_config_file)
    return config_filepath


@patch("monopyly.Flask.debug", new=True)
def test_development_config():
    app = create_app()
    assert app.config["SECRET_KEY"] == "development key"


def test_production_config(default_config_file):
    app = create_app()
    assert app.config["SECRET_KEY"] not in ["development key", "testing key"]


def test_production_config_default_file(default_config_file):
    with patch(
        "monopyly.config.settings.ProductionConfig.config_filepaths",
        new=[default_config_file],
    ):
        config = ProductionConfig()
        assert config.SECRET_KEY == "test secret key"


def test_production_config_instance_file(
    default_config_file, instance_path, instance_config_file
):
    with patch(
        "monopyly.config.default_settings.Config.config_filepaths",
        new=[default_config_file],
    ):
        config = ProductionConfig.configure_for_instance(instance_path)
        print(config.config_filepaths)
        assert config.SECRET_KEY == "test secret key"
        assert config.OTHER == "test supersede"


@patch("monopyly.database.SQLAlchemy.initialize")
def test_test_config(mock_init_db_method):
    assert not create_app().testing
    mock_db_path = "/path/to/test/db.sqlite"
    app = create_app(_TestingConfig(db_path=mock_db_path))
    assert app.testing
    assert app.config["SECRET_KEY"] == "testing key"
    assert app.config["DATABASE"] == Path(mock_db_path)
