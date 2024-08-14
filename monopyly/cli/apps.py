"""Application objects for running the app via the CLI."""

import multiprocessing
import subprocess

from gunicorn.app.base import BaseApplication

from .. import create_app


class LocalApplication:
    """
    An object for running the application locally.

    This application object will run the Flask application using the
    built-in Python server on localhost, just like the Flask development
    mode. However, it will launch from port 5001 to avoid conflicting
    with other Python servers that may attempt to run on the default
    port 5000.
    """

    mode_name = "local"
    default_port = "5001"
    _debug = None

    def __init__(self, host=None, port=None, **options):
        """Initialize the application in development mode."""
        self._host = host
        self._port = port or self.default_port
        if options:
            raise NotImplementedError(
                f"Options besides `host` and `port` are not handled in {self.mode_name} mode."
            )
        self.application = create_app(debug=self._debug)

    def run(self):
        """Run the Monopyly application in development mode."""
        self.application.run(
            host=self._host,
            port=self._port,
            debug=self._debug,
        )


class DevelopmentApplication(LocalApplication):
    """
    An object for running the application in development mode.

    This application object will run the Flask application using the
    built-in Python server on localhost, just like the Flask development
    mode.
    """

    mode_name = "development"
    default_port = None  # traditionally 5000
    _debug = True


class ProductionApplication(BaseApplication):
    """
    An object for running the application in production mode (via Gunicorn).

    This application object will run the Flask application using a
    Gunicorn server instead of the built-in Python server.
    """

    default_port = None  # traditionally 8000
    _default_worker_count = (multiprocessing.cpu_count() * 2) + 1

    def __init__(self, host=None, port=None, **options):
        """Initialize the application in production mode."""
        if port and not host:
            raise ValueError("A host must be specified when the port is given.")
        self._host = host
        self._port = port or self.default_port
        self.options = options
        self.options["bind"] = self._determine_binding(options.get("bind"))
        self.options.setdefault("workers", self._default_worker_count)
        self.application = create_app()
        super().__init__()

    def _determine_binding(self, bind_option):
        # Parse any socket binding options
        if self._host and bind_option:
            raise ValueError(
                "The `host` may not be specified directly if the `bind` option is used."
            )
        if self._host:
            bind_values = [self._host]
            if self._port:
                bind_values.append(self._port)
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
