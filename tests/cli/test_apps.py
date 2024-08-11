"""Tests for applications launched from the command line."""

import multiprocessing
from abc import ABC, abstractmethod
from unittest.mock import call, patch

import pytest
from flask import Flask

from monopyly.cli.apps import (
    DevelopmentApplication,
    LocalApplication,
    ProductionApplication,
)


class _TestApplication(ABC):

    @property
    @abstractmethod
    def app_cls(self):
        raise NotImplementedError("Define the application class in a subclass.")

    @property
    @abstractmethod
    def app_default_port(self):
        raise NotImplementedError("Define the default port in a subclass.")


class TestLocalApplication(_TestApplication):
    app_cls = LocalApplication
    app_default_port = "5001"
    app_debugging = None

    def test_initialization(self):
        self.app_cls(host="test.host", port="0000")

    def test_initialization_invalid(self):
        with pytest.raises(NotImplementedError):
            self.app_cls(host="test.host", port="0000", option="invalid option")

    @patch("monopyly.cli.apps.create_app")
    def test_run(self, mock_app_creator):
        mock_flask_app = mock_app_creator.return_value
        app = self.app_cls(host="test.host", port="0000")
        app.run()
        mock_flask_app.run.assert_called_once_with(
            host="test.host", port="0000", debug=self.app_debugging
        )

    @patch("monopyly.cli.apps.create_app")
    def test_run_defaults(self, mock_app_creator):
        mock_flask_app = mock_app_creator.return_value
        app = self.app_cls()
        app.run()
        mock_flask_app.run.assert_called_once_with(
            host=None, port=self.app_default_port, debug=self.app_debugging
        )


class TestDevelopmentApplication(TestLocalApplication):
    app_cls = DevelopmentApplication
    app_default_port = None
    app_debugging = True


class TestProductionApplication(_TestApplication):
    app_cls = ProductionApplication
    app_default_port = "8000"
    expected_worker_count = (multiprocessing.cpu_count() * 2) + 1

    def test_initialization(self):
        app = self.app_cls(host="test.host", port="0000")
        assert isinstance(app.application, Flask)
        assert app.options == {
            "bind": "test.host:0000",
            "workers": self.expected_worker_count,
        }

    def test_initialization_via_bind(self):
        app = self.app_cls(bind="test.host:0000")
        assert isinstance(app.application, Flask)
        assert app.options == {
            "bind": "test.host:0000",
            "workers": self.expected_worker_count,
        }

    @pytest.mark.parametrize(
        "invalid_kwargs, exception",
        [
            [
                {"host": "test.host", "port": "0000", "bind": "test.alt.host:9999"},
                ValueError,
            ],
            [{"port": "0000"}, ValueError],
        ],
    )
    def test_initialization_invalid(self, invalid_kwargs, exception):
        with pytest.raises(exception):
            self.app_cls(**invalid_kwargs)

    @pytest.mark.xfail
    def test_load_config(self):
        assert False

    def test_load(self):
        app = self.app_cls(host="test.host", port="0000")
        assert app.load() is app.application

    @patch("gunicorn.config.Config.set")
    @patch("gunicorn.app.base.BaseApplication.run")
    def test_run(self, mock_gunicorn_run_method, mock_gunicorn_config_set_method):
        app = self.app_cls(host="test.host", port="0000")
        app.run()
        mock_gunicorn_run_method.assert_called_once()
        mock_gunicorn_config_set_method.assert_has_calls(
            [
                call("bind", "test.host:0000"),
                call("workers", self.expected_worker_count),
            ]
        )

    @patch("gunicorn.config.Config.set")
    @patch("gunicorn.app.base.BaseApplication.run")
    def test_run_defaults(
        self, mock_gunicorn_run_method, mock_gunicorn_config_set_method
    ):
        app = self.app_cls()
        app.run()
        mock_gunicorn_run_method.assert_called_once()
        mock_gunicorn_config_set_method.assert_has_calls(
            [call("workers", self.expected_worker_count)]
        )
