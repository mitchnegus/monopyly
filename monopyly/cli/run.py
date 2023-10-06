#!/usr/bin/env python
"""
A script (entry point) to launch the Monopyly application.
"""
import argparse
import os
import signal
import subprocess
import time
import webbrowser
from pathlib import Path
from threading import Event

from flask import current_app
from rich.console import Console

from .apps import DevelopmentApplication, LocalApplication, ProductionApplication

# Set the Flask environment variable
os.environ["FLASK_APP"] = "monopyly"


def main():
    args = parse_arguments()
    app_launcher = Launcher(args.mode, host=args.host, port=args.port)
    # Initialize the database and run the app
    app_launcher.initialize_database()
    if args.backup:
        app_launcher.backup_database()
    app_launcher.launch()
    if args.mode in ("development", "local"):
        # Enable browser viewing in development mode
        if args.browser:
            app_launcher.open_browser(delay=1)
        # Wait for the exit command to stop
        app_launcher.wait_for_exit()


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", help="the host address where the app will be run")
    parser.add_argument("--port", help="the port where the app will be accessible")
    parser.add_argument(
        "--backup",
        action="store_true",
        help="a flag indicating if the database should be backed up",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help=(
            "a flag indicating if a new browser window should be opened (development "
            "and local modes only)"
        ),
    )
    parser.add_argument(
        "mode",
        help="the runtime mode for the app",
        choices=["development", "local", "production"],
    )
    return parser.parse_args()


class Launcher:
    """A tool to build and execute Flask commands."""

    _application_types = {
        "development": DevelopmentApplication,
        "local": LocalApplication,
        "production": ProductionApplication,
    }
    _console = Console()
    _exit = Event()
    command = ["flask"]

    def __init__(self, mode, host=None, port=None):
        app_type = self._application_types[mode]
        if mode == "development":
            self.command = self.command + ["--debug"]
        self.host = host if host else "127.0.0.1"
        self.port = port if port else app_type.default_port
        self.app = app_type(host=self.host, port=self.port)

    def initialize_database(self):
        """Run the database initializer."""
        instruction = self.command + ["init-db"]
        self._console.print("[deep_sky_blue1]Initializing the database...")
        subprocess.run(instruction)
        print("\n")

    def backup_database(self):
        """Back up the app database."""
        self._console.print("[deep_sky_blue1]Backing up the database...")
        instruction = self.command + ["back-up-db"]
        subprocess.run(instruction)
        print("\n")

    def launch(self):
        """Launch the Monopyly application."""
        self._console.print("[deep_sky_blue1]Running the Monopyly application...\n")
        self.app.run()

    def open_browser(self, delay=0):
        """Open the default web browser."""
        time.sleep(delay)
        webbrowser.open(f"http://{self.host}:{self.port}/")

    @classmethod
    def wait_for_exit(cls):
        """Wait for the exit command (e.g., keyboard interrupt) to be issued."""
        for sig in ("TERM", "HUP", "INT"):
            signal.signal(getattr(signal, "SIG" + sig), cls._quit)
        while not cls._exit.is_set():
            cls._exit.wait(1)

    @classmethod
    def _quit(cls, signo, _frame):
        """Send the signal to quit the app."""
        print("\nClosing the Monopyly app...")
        cls._exit.set()


if __name__ == "__main__":
    main()
