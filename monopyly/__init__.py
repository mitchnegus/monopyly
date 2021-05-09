"""
Run a development server for the Monopyly app.
"""
import os
from flask import Flask

from monopyly.db import db
from monopyly.core import core
from monopyly.auth import auth
from monopyly.credit import credit
from monopyly.banking import banking


def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='development key',
        DATABASE=os.path.join(app.instance_path, 'monopyly.sqlite')
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if that is passed instead
        app.config.from_mapping(test_config)

    # Ensure that the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Allow the databases to be initialized from the command line
    db.init_app(app)

    # Register the core functionality blueprint
    app.register_blueprint(core)

    # Register the authentication blueprint
    app.register_blueprint(auth)

    # Register the banking financials blueprint
    app.register_blueprint(banking)

    # Register the credit card financials blueprint
    app.register_blueprint(credit)

    return app
