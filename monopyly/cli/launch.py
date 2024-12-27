#!/usr/bin/env python
"""
A script (entry point) to launch the Monopyly application.
"""
import os
import time
import webbrowser
from functools import partial

import click
from werkzeug.serving import is_running_from_reloader

from ..database import back_up_db, init_db
from .console import echo_text
from .modes import DevelopmentAppMode, LocalAppMode, ProductionAppMode

APP_TYPES = [DevelopmentAppMode, LocalAppMode, ProductionAppMode]


class Launcher:
    """A tool to build and execute Flask commands."""

    _application_types = {app_type.name: app_type for app_type in APP_TYPES}
    _loaded_env_var = "MONOPYLY_LOADED"
    _browser_env_var = "MONOPYLY_BROWSER"

    def __init__(self, context, mode, host=None, port=None, backup=None, browser=False):
        self.mode = mode
        application_type = self._application_types[mode]
        # Set attributes to govern launch control flow
        self._backup = backup
        self._use_browser = browser
        self.host = host if host else "127.0.0.1"
        self.port = port if port else application_type.default_port
        # Perform initialization actions
        self.application = self._build_application(application_type, context)
        if not self.is_loaded:
            init_db()

    def _build_application(self, application_type, context):
        return application_type(context, host=self.host, port=self.port)

    def launch(self):
        """Launch the Monopyly application."""
        if self._backup:
            back_up_db()
        open_browser_criteria = [
            self._use_browser,
            not self.has_browser,
            not is_running_from_reloader(),
        ]
        if all(open_browser_criteria):
            self.open_browser()
        try:
            self._run_application()
        finally:
            self._close_application()

    def _run_application(self):
        if not self.is_loaded:
            echo_text("Running the Monopyly application...\n", color="deep_sky_blue1")
            self.is_loaded = True
        self.application.run()

    def _close_application(self):
        if not (is_running_from_reloader() or self.mode == "production"):
            echo_text("\nClosing the Monopyly app...")
            self.is_loaded = False

    def open_browser(self, delay=0):
        """Open the default web browser."""
        if self.mode in ("development", "local"):
            time.sleep(delay)
            webbrowser.open_new(f"http://{self.host}:{self.port}/")
            self.has_browser = True
        else:
            raise RuntimeError(
                "Opening the browser is only supported in development or local mode."
            )

    @property
    def is_loaded(self):
        return self._get_boolean_env_variable(self._loaded_env_var)

    @is_loaded.setter
    def is_loaded(self, value):
        self._set_booean_env_variable(self._loaded_env_var, value)

    @property
    def has_browser(self):
        return self._get_boolean_env_variable(self._browser_env_var)

    @has_browser.setter
    def has_browser(self, value):
        self._set_booean_env_variable(self._browser_env_var, value)

    @staticmethod
    def _get_boolean_env_variable(name):
        return bool(os.environ.get(name))

    @staticmethod
    def _set_booean_env_variable(name, value):
        if value:
            os.environ[name] = "true"
        else:
            os.environ.pop(name)


@click.command(
    "launch",
    help="Launch the application.",
)
@click.argument(
    "mode",
    type=click.Choice(["development", "local", "production"], case_sensitive=False),
)
@click.option("--host", "-h", type=click.STRING, help="The interface to bind to.")
@click.option("--port", "-p", type=click.INT, help="The port to bind to.")
@click.option(
    "--backup",
    is_flag=True,
    help="A flag indicating if the database should be backed up.",
)
@click.option(
    "--browser",
    is_flag=True,
    help=(
        "A flag indicating if a new browser window should be opened "
        "(development and local modes only)."
    ),
)
@click.pass_context
def launch_command(context, mode, host, port, backup, browser):
    """Run the app as a command line program."""
    app_launcher = Launcher(
        context, mode, host=host, port=port, backup=backup, browser=browser
    )
    app_launcher.launch()
