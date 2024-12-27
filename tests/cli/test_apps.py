"""Tests for applications launched from the command line."""

import multiprocessing
from abc import ABC, abstractmethod
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from flask import Flask

from monopyly import create_app
from monopyly.cli.modes import DevelopmentAppMode, LocalAppMode, ProductionAppMode


@pytest.fixture
def mock_context(app):
    context = Mock()
    context.obj.create_app.return_value = app
    context.obj.load_app.return_value = app
    return context


def mock_configuration(**parameters):
    config = MagicMock()
    config.get.side_effect = parameters.get
    config.__getitem__.side_effect = parameters.__getitem__
    return config


class _TestAppMode(ABC):

    @property
    @abstractmethod
    def app_mode_cls(self):
        raise NotImplementedError("Define the application mode in a subclass.")

    @property
    @abstractmethod
    def app_default_port(self):
        raise NotImplementedError("Define the default port in a subclass.")


class TestLocalAppMode(_TestAppMode):
    app_mode_cls = LocalAppMode
    app_default_port = 5001
    app_debugging = False

    def test_initialization(self, mock_context):
        self.app_mode_cls(mock_context, host="test.host", port=1111)

    def test_initialization_invalid(self, mock_context):
        with pytest.raises(NotImplementedError):
            self.app_mode_cls(
                mock_context, host="test.host", port=1111, option="invalid option"
            )

    @patch("monopyly.cli.modes.run_command")
    @patch("os.environ")
    def test_run(self, mock_environment, mock_run_command, mock_context):
        mock_flask_app = mock_context.obj.create_app.return_value
        with patch.object(mock_flask_app, "config", new=mock_configuration()):
            app_mode = self.app_mode_cls(mock_context, host="test.host", port=1111)
            app_mode.run()
            mock_environment.setdefault.assert_called_once_with(
                "FLASK_DEBUG", str(self.app_debugging)
            )
            mock_context.invoke.assert_called_once_with(
                mock_run_command, host="test.host", port=1111
            )

    @patch("monopyly.cli.modes.run_command")
    @patch("os.environ")
    def test_run_defaults(self, mock_environment, mock_run_command, mock_context):
        mock_flask_app = mock_context.obj.create_app.return_value
        with patch.object(mock_flask_app, "config", new=mock_configuration()):
            app_mode = self.app_mode_cls(mock_context)
            app_mode.run()
            mock_environment.setdefault.assert_called_once_with(
                "FLASK_DEBUG", str(self.app_debugging)
            )
            mock_context.invoke.assert_called_once_with(
                mock_run_command, host=None, port=self.app_default_port
            )

    @patch("monopyly.cli.modes.run_command")
    @patch("os.environ")
    def test_run_from_configuration(
        self, mock_environment, mock_run_command, mock_context
    ):
        mock_flask_app = mock_context.obj.create_app.return_value
        with patch.object(
            mock_flask_app,
            "config",
            new=mock_configuration(SERVER_NAME="test.host:1111"),
        ):
            app_mode = self.app_mode_cls(mock_context)
            app_mode.run()
            mock_environment.setdefault.assert_called_once_with(
                "FLASK_DEBUG", str(self.app_debugging)
            )
            mock_context.invoke.assert_called_once_with(
                mock_run_command, host="test.host", port=1111
            )


class TestDevelopmentAppMode(TestLocalAppMode):
    app_mode_cls = DevelopmentAppMode
    app_default_port = 5000
    app_debugging = True


class TestProductionAppMode(_TestAppMode):
    app_mode_cls = ProductionAppMode
    app_default_port = 8000
    expected_worker_count = (multiprocessing.cpu_count() * 2) + 1

    def test_initialization(self, mock_context):
        app_mode = self.app_mode_cls(mock_context, host="test.host", port=1111)
        assert isinstance(app_mode.application, Flask)
        assert app_mode.options == {
            "bind": "test.host:1111",
            "workers": self.expected_worker_count,
        }

    def test_initialization_via_bind(self, mock_context):
        app_mode = self.app_mode_cls(mock_context, bind="test.host:1111")
        assert isinstance(app_mode.application, Flask)
        assert app_mode.options == {
            "bind": "test.host:1111",
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
    def test_initialization_invalid(self, mock_context, invalid_kwargs, exception):
        with pytest.raises(exception):
            self.app_mode_cls(mock_context, **invalid_kwargs)

    @pytest.mark.xfail
    def test_load_config(self):
        assert False

    def test_load(self, mock_context):
        app_mode = self.app_mode_cls(mock_context, host="test.host", port=1111)
        assert app_mode.load() is app_mode.application

    @patch("gunicorn.config.Config.set")
    @patch("gunicorn.app.base.BaseApplication.run")
    def test_run(
        self, mock_gunicorn_run_method, mock_gunicorn_config_set_method, mock_context
    ):
        app_mode = self.app_mode_cls(mock_context, host="test.host", port=1111)
        app_mode.run()
        mock_gunicorn_run_method.assert_called_once()
        mock_gunicorn_config_set_method.assert_has_calls(
            [
                call("bind", "test.host:1111"),
                call("workers", self.expected_worker_count),
            ]
        )

    @patch("gunicorn.config.Config.set")
    @patch("gunicorn.app.base.BaseApplication.run")
    def test_run_defaults(
        self, mock_gunicorn_run_method, mock_gunicorn_config_set_method, mock_context
    ):
        app_mode = self.app_mode_cls(mock_context)
        app_mode.run()
        mock_gunicorn_run_method.assert_called_once()
        mock_gunicorn_config_set_method.assert_has_calls(
            [call("workers", self.expected_worker_count)]
        )
