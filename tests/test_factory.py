"""Tests for the application factory."""
from monopyly import create_app


def test_config():
    assert not create_app().testing
    assert create_app({'TESTING': True}).testing
