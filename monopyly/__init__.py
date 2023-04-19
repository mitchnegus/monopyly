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
    db,
    init_db_command,
)


def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    # Prepare the app configuration
    if test_config:
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

    # Initialize the app, including CLI commands and blueprints
    init_app(app)
    return app


def _get_preload_data_path(instance_path):
    dev_data_path = instance_path / "preload_dev_data.sql"
    return dev_data_path if dev_data_path.exists() else None


@SQLAlchemy.interface_selector(db)
def init_app(app):
    """Initialize the app."""
    register_blueprints(app)
    # Register the database actions with the app
    app.cli.add_command(init_db_command)
    app.cli.add_command(back_up_db_command)


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
