"""
Run the Monopyly app.
"""

from flask import Flask

from monopyly.config import DevelopmentConfig, ProductionConfig
from monopyly.core.errors import render_error_template
from monopyly.database import SQLAlchemy, register_db_cli_commands


def create_app(test_config=None, debug=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    # Prepare the app configuration
    if test_config:
        config = test_config
    else:
        # Load the development/production config when not testing
        if app.debug or debug:
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
    register_errorhandlers(app)
    register_db_cli_commands(app)


def register_blueprints(app):
    """
    Register blueprints with the app.

    Notes
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


def register_errorhandlers(app):
    """Register error handlers with the app."""
    handled_error_codes = [
        400,
        401,
        403,
        404,
        405,
        408,
        418,
        # 425 -- not yet supported
        500,
    ]
    for code in handled_error_codes:
        app.register_error_handler(code, render_error_template)
