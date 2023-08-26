"""Application objects for running the app via the CLI."""
import multiprocessing
import subprocess

from gunicorn.app.base import BaseApplication

from .. import create_app


class LocalApplication:
    """An object for running the application locally."""

    default_port = "5001"
    command = ["flask"]

    def __init__(self, host=None, port=None, **options):
        """Initialize the application in development mode."""
        self._host = host
        self._port = port
        if options:
            raise NotImplementedError(
                "Options besides `host` and `port` are not handled in development mode."
            )

    def run(self):
        """Run the Monopyly application in development mode."""
        instruction = self.command + ["run"]
        if self._host:
            instruction += ["--host", self._host]
        if self._port:
            instruction += ["--port", self._port]
        server = subprocess.Popen(instruction)


class DevelopmentApplication(LocalApplication):
    """An object for running the application in development mode."""

    default_port = "5000"
    command = LocalApplication.command + ["--debug"]


class ProductionApplication(BaseApplication):
    """An object for running the application in production mode (via Gunicorn)."""

    default_port = "8000"
    _default_worker_count = (multiprocessing.cpu_count() * 2) + 1

    def __init__(self, host=None, port=None, **options):
        """Initialize the application in production mode."""
        options["bind"] = self._parse_binding(host, port, options.get("bind"))
        options.setdefault("workers", self._default_worker_count)
        self.options = options
        self.application = create_app()
        super().__init__()

    @staticmethod
    def _parse_binding(host, port, bind_option):
        # Parse any socket binding options
        if (host or port) and bind_option:
            raise ValueError(
                "Neither `host` nor `port` parameters can be specified if the "
                "`bind` option is given."
            )
        bind_values = []
        if host:
            bind_values.append(host)
        if port:
            bind_values.append(port)
        return bind if (bind := ":".join(bind_values)) else bind_option

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
