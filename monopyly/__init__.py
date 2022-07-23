"""
Run a development server for the Monopyly app.
"""
import os
from flask import Flask

from monopyly import db
from monopyly.core import core_bp
from monopyly.auth import auth_bp
from monopyly.credit import credit_bp
from monopyly.banking import banking_bp


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

    # Allow the databases to be initialized from the command line
    _ensure_instance_directory_exists(app)
    db.init_app(app)
    # Register the core functionality blueprint
    app.register_blueprint(core_bp)
    # Register the authentication blueprint
    app.register_blueprint(auth_bp)
    # Register the banking financials blueprint
    app.register_blueprint(banking_bp)
    # Register the credit card financials blueprint
    app.register_blueprint(credit_bp)

    return app


def _ensure_instance_directory_exists(app):
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
