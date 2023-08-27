"""
Run a development server for the Monopyly app.
"""
from flask import Flask

from monopyly.config import DevelopmentConfig, ProductionConfig
from monopyly.database import SQLAlchemy, register_db_cli_commands


def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    # Prepare the app configuration
    if test_config:
        config = test_config
    else:
        # Load the development/production config when not testing
        if app.debug:
            config = DevelopmentConfig.configure_for_instance(app.instance_path)
        else:
            config = ProductionConfig.configure_for_instance(app.instance_path)
    app.config.from_object(config)

    # Initialize the app, including CLI commands and blueprints
    init_app(app)
    return app


@SQLAlchemy.interface_selector
def init_app(app):
    """Initialize the app."""
    register_blueprints(app)
    register_db_cli_commands(app)


def register_blueprints(app):
    """
    Register blueprints with the app.

    Note
    -----
    Blueprints are imported in this function to avoid loading modules
    that require database models before those models have been set up
    via `init_app`. (Rendered obsolete using Authanor; retained in order
    to keep blueprint imports grouped.)
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
