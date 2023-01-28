"""Tests for the application factory."""
from monopyly import create_app
# Rename config to avoid Pytest attempting to collect `TestingConfig`
from monopyly.config import TestingConfig as _TestingConfig


def test_config():
    assert not create_app().testing
    assert create_app(_TestingConfig).testing
