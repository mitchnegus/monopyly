"""
Run a development server for the Monopyly app.
"""
import warnings
from pathlib import Path

from flask import Flask

from monopyly.config import DevelopmentConfig, ProductionConfig
from monopyly.database import (
    DB_NAME,
    SQLAlchemy,
    back_up_db_command,
    close_db,
    db,
    init_db_command,
)


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
        if app.debug:
            db_path = instance_path / f"dev-{DB_NAME}"
            preload_data_path = _get_preload_data_path(instance_path)
            config = DevelopmentConfig(
                db_path=db_path, preload_data_path=preload_data_path
            )
        else:
            db_path = instance_path / DB_NAME
            config = ProductionConfig(db_path=db_path)
            # Give a while the secret key remains insecure
            warnings.formatwarning = lambda msg, *args, **kwargs: f"\n{msg}\n"
            warnings.warn("INSECURE: Production mode has not yet been fully configured")
    app.config.from_object(config)

    # Allow the databases to be initialized from the command line
    init_app(app)
    register_blueprints(app)
    return app


def _get_preload_data_path(instance_path):
    dev_data_path = instance_path / "preload_dev_data.sql"
    return dev_data_path if dev_data_path.exists() else None


def init_app(app):
    """Initialize the app."""
    # Establish behavior for closing the database
    app.teardown_appcontext(close_db)
    # Register the database actions with the app
    app.cli.add_command(init_db_command)
    app.cli.add_command(back_up_db_command)
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

    Note
    -----
    Blueprints are imported in this function to avoid loading modules
    that require database models before those models have been set up
    via `init_app`.
    """
    # Import blueprints
    from monopyly.auth.blueprint import bp as auth_bp
    from monopyly.banking.blueprint import bp as banking_bp
    from monopyly.core.blueprint import bp as core_bp
    from monopyly.credit.blueprint import bp as credit_bp

    # Register blueprints
    app.register_blueprint(core_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(banking_bp)
    app.register_blueprint(credit_bp)
