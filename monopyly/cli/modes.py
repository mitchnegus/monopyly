"""Application objects for running the app via the CLI."""

import multiprocessing
import os
from abc import ABC, abstractmethod

from flask.cli import run_command
from gunicorn.app.base import BaseApplication

from .. import AppFactory
from ..config import DevelopmentConfig, ProductionConfig, TestingConfig


class CustomCLIAppMode(ABC):
    """
    An abstract mixin for running a Flask-based application with a custom CLI.

    This object is designed to allow the typical Flask application CLI
    to be customized so that apps can be created (and launched) using
    a specified mode (e.g., locally launched applications, development
    applications, and production-level applications.

    Parameters
    ----------
    context : click.core.Context
        The click context that is created by running the application
        from the command line via a click command.
    *args :
        Positional arguments to be passed to other parent classes
        during instantiaion (other than the click context).
    **kwargs :
        Keyword arguments to be passed to other parent classes
        during instantiaion (other than the click context).

    Notes
    -----
    This object exists because (as of Flask version 3.0.3) CLI
    invocations appear to hardcode some calls to the `create_app`
    function—an application factory—without accepting arguments. The
    factory function is set on the Flask `ScriptInfo` object (via the
    `obj` attribute), and so the instantiation this class creates an
    instance of an `AppFactory` object which is aware of the app mode
    to use when creating the app. This effectively embeds the app mode
    information into the `create_app` factory function/method.
    """

    config_type = None

    def __init__(self, context, *args, **kwargs):
        self._context = context
        # Set the app factory to pass the app mode even when called with no arguments
        self._context.obj.create_app = AppFactory(self).create_app
        self.application = self._context.obj.load_app()
        super().__init__(*args, **kwargs)

    @property
    @abstractmethod
    def name(self):
        raise NotImplementedError(
            "Define the name of the custom CLI mode in a subclass."
        )

    @classmethod
    def define_instance_configuration(cls, app):
        return cls.config_type.configure_for_instance(app.instance_path)


class LocalAppMode(CustomCLIAppMode):
    """
    An object for running the application locally.

    This application object will run the Flask application using the
    built-in Python server on localhost, just like the Flask development
    mode. However, it will launch from port 5001 to avoid conflicting
    with other Python servers that may attempt to run on the default
    port 5000.
    """

    name = "local"
    config_type = ProductionConfig  # local apps have a production configuration
    default_port = 5001
    _debug = False

    def __init__(self, context, host=None, port=None, **options):
        """Initialize the application in development mode."""
        super().__init__(context)
        self._host, self._port = self._determine_server(host, port)
        if options:
            raise NotImplementedError(
                "Options besides `host` and `port` are not handled in "
                f"{self.name} mode."
            )

    def _determine_server(self, host, port):
        # Use the Flask application host/port if configured (and not explicitly set)
        if server_name := self.application.config.get("SERVER_NAME"):
            server_name_host, _, server_name_port = server_name.partition(":")
            host = host or server_name_host
            port = port or int(server_name_port)
        # Use the default port if no other is specified
        port = port or self.default_port
        return host, port

    def run(self):
        """
        Run the Monopyly application in development mode.

        Notes
        -----
        This app uses the `invoke` method of a click `Context` object
        to reproduce the standard behavior of `flask run` when running
        the Monopyly app from the command line. Where Flask's run
        command parses the `FLASK_DEBUG` environment variale (rather
        than accepting `--debug` as an argument directly), this method
        adjusts the environment variable to match the default debug
        setting of this application type. If the `FLASK_DEBUG` variable
        is already set, it will override the application type's default
        value.
        """
        os.environ.setdefault("FLASK_DEBUG", str(self._debug))
        self._context.invoke(run_command, host=self._host, port=self._port)


class DevelopmentAppMode(LocalAppMode):
    """
    An object for running the application in development mode.

    This application object will run the Flask application using the
    built-in Python server on localhost, just like the Flask development
    mode.
    """

    name = "development"
    config_type = DevelopmentConfig
    default_port = 5000  # traditionally 5000 (set by Flask)
    _debug = True


class ProductionAppMode(CustomCLIAppMode, BaseApplication):
    """
    An object for running the application in production mode (via Gunicorn).

    This application object will run the Flask application using a
    Gunicorn server instead of the built-in Python server.
    """

    name = "production"
    config_type = ProductionConfig
    default_port = 8000  # traditionally 8000 (set by Gunicorn)
    _default_worker_count = (multiprocessing.cpu_count() * 2) + 1

    def __init__(self, context, host=None, port=None, **options):
        if port and not host:
            raise ValueError("A host must be specified when the port is given.")
        self._host = host
        self._port = port or self.default_port
        self.options = options
        self.options["bind"] = self._determine_binding(options.get("bind"))
        self.options.setdefault("workers", self._default_worker_count)
        super().__init__(context)

    def _determine_binding(self, bind_option):
        # Parse any socket binding options
        if self._host and bind_option:
            raise ValueError(
                "The `host` may not be specified directly if the `bind` option is used."
            )
        if self._host:
            bind_values = [self._host]
            if self._port:
                bind_values.append(str(self._port))
            bind_option = ":".join(bind_values)
        return bind_option

    def load_config(self):
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

    def run(self, *args, **kwargs):
        return super().run(*args, **kwargs)
