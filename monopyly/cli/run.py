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

# Set the Flask environment variable
os.environ["FLASK_APP"] = "monopyly"


def main():
    args = parse_arguments()
    app_runner = Runner(args.mode, host=args.host, port=args.port)
    # Initialize the database and run the app
    app_runner.initialize_database()
    if args.backup:
        app_runner.backup_database()
    app_runner.run()
    app_runner.open_browser(delay=1)
    # Wait for the exit command to stop
    app_runner.wait_for_exit()


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", help="The host address where the app will be run.")
    parser.add_argument("--port", help="The port where the app will be accessible.")
    parser.add_argument(
        "--backup",
        action="store_true",
        help="A flag indicating if the database should be backed up.",
    )
    parser.add_argument(
        "mode",
        help="The runtime mode for the app; defaults to `development`.",
        choices=["development", "production"],
    )
    return parser.parse_args()


class Runner:
    """A tool to build and execute Flask commands."""

    _exit = Event()

    def __init__(self, mode, host=None, port=None):
        self.mode = mode
        self.host = host
        self.port = port if port else "5000"

    @property
    def command(self):
        _command = ["flask"]
        if self.mode == "development":
            _command.append("--debug")
        return _command

    def initialize_database(self):
        """Run the database initializer."""
        instruction = self.command + ["init-db"]
        subprocess.run(instruction)

    def backup_database(self):
        """Back up the app database."""
        instruction = self.command + ["back-up-db"]
        subprocess.run(instruction)

    def run(self):
        """Run the Monopyly application."""
        instruction = self.command + ["run"]
        if self.host:
            instruction += ["--host", self.host]
        if self.port:
            instruction += ["--port", self.port]
        server = subprocess.Popen(instruction)

    def open_browser(self, delay=0):
        """Open the default web browser."""
        time.sleep(delay)
        webbrowser.open(f"http://127.0.0.1:{self.port}/")

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
