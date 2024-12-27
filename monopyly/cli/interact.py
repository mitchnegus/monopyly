"""
A script providing CLI functionality for the Monopyly application.

Built on Flask, the Monopyly command line interface extends the typical
Flask CLI to include additional commands for launching the application,
initializing the applicaiton database, and backing up the application
database.
"""

import os

from flask.cli import FlaskGroup

from .launch import launch_command


def main():
    # Set the `FLASK_APP` environment variable required by Flask
    os.environ["FLASK_APP"] = "monopyly"
    # Create a `FlaskGroup` object for managing the CLI
    cli = FlaskGroup(name="monopyly", help=__doc__)
    cli.add_command(launch_command)
    cli.main()


if __name__ == "__main__":
    main()
