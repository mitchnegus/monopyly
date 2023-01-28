"""
Run a development server for the Monopyly app.
"""
from pathlib import Path
from warnings import warn

from flask import Flask

from monopyly.config import DevelopmentConfig, ProductionConfig
from monopyly.database import db, SQLAlchemy, init_db_command, close_db, DB_NAME


def create_app(test_config=None):
    # Create and configure the app
    app = Flask(
        __name__,
        instance_relative_config=True,
    )

    if test_config:
        # Load the test config if that is passed instead
        config = test_config
    else:
        # Ensure the instance path exists
        instance_path = Path(app.instance_path)
        instance_path.mkdir(parents=True, exist_ok=True)
        # Load the development/production config when not testing
        db_path = instance_path / DB_NAME
        if app.debug:
            config = DevelopmentConfig(db_path=db_path)
        else:
            config = ProductionConfig(db_path=db_path)
            warn("INSECURE: Production mode has not yet been fully configured")
    app.config.from_object(config)

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
    #   - Use the `app.db` attribute like the `app.extensions` dict
    #     (but not actually that dict because this is not an extension)
    if app.testing:
        app.db = SQLAlchemy()
    else:
        app.db = db
    app.db.setup_engine(db_path=app.config["DATABASE"])
    # If the database is new, it will not yet have been properly populated
    if not app.testing and Path(app.config["DATABASE"]).exists():
        app.db.access_tables()


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

