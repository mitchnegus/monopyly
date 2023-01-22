"""
Run a development server for the Monopyly app.
"""
from pathlib import Path

from flask import Flask

from monopyly.database import db, init_db_command, close_db, DB_PATH
from monopyly.definitions import INSTANCE_PATH


def create_app(test_config=None):
    # Ensure that the instance path exists
    INSTANCE_PATH.mkdir(parents=True, exist_ok=True)
    # Create and configure the app
    app = Flask(
        __name__,
        instance_path=INSTANCE_PATH.resolve(),
        instance_relative_config=True,
    )
    app.config.from_mapping(
        SECRET_KEY='development key',
        DATABASE=DB_PATH,
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if that is passed instead
        app.config.from_mapping(test_config)

    # Allow the databases to be initialized from the command line
    init_app(app)
    register_blueprints(app)
    return app


def init_app(app):
    """Initialize the app."""
    # Establish behavior for closing the database
    app.teardown_appcontext(close_db)
    # Register the database intialization with the app
    app.cli.add_command(init_db_command)
    # Prepare database access with SQLAlchemy
    db.setup_engine()
    if not app.config["TESTING"] and Path(app.config["DATABASE"]).exists():
        db.access_tables()


def register_blueprints(app):
    """
    Register blueprints with the app.

    Notes
    -----
    Blueprints are imported in this function to avoid loading modules
    that require database models before those models have been set up
    via `init_app`.
    """
    # Register the core functionality blueprint
    from monopyly.core.blueprint import bp as core_bp
    app.register_blueprint(core_bp)
    # Register the authentication blueprint
    from monopyly.auth.blueprint import bp as auth_bp
    app.register_blueprint(auth_bp)
    # Register the banking financials blueprint
    from monopyly.banking.blueprint import bp as banking_bp
    app.register_blueprint(banking_bp)
    # Register the credit card financials blueprint
    from monopyly.credit.blueprint import bp as credit_bp
    app.register_blueprint(credit_bp)

