"""
Run the Monopyly app.
"""

from flask import Flask

from .config import DevelopmentConfig, ProductionConfig, TestingConfig
from .core.errors import render_error_template
from .database import SQLAlchemy, register_db_cli_commands


def create_app(config=None):
    """Create the Monopyly application."""
    return AppFactory().create_app(config)


class AppFactory:
    """
    An application factory for the Flask app.

    Parameters
    ----------
    app_mode : monopyly.cli.modes.CustomCLIAppMode, None
        The application mode to use when determining application
        configurations beyond those specified in a configuration object
        provided to the factory function.
    """

    def __init__(self, app_mode=None):
        self._app_mode = app_mode

    def create_app(self, config=None):
        """
        Create the Flask application.

        Create the Flask app, including configurations as specified. This
        will configure the app using the configuration objects made
        available by the Monopyly application and initialize the app
        by registering app blueprints, routes, and commands.
        """
        # Create and configure the app
        app = Flask(__name__, instance_relative_config=True)
        self._configure_app(app, config)
        # Initialize the app, including CLI commands and blueprints
        init_app(app)
        return app

    def _configure_app(self, app, config):
        """Configure the application for the stated mode (and optional configuration)."""
        # Load the default mode configuration when not otherwise specified
        # (including testing)
        if not config:
            if self._app_mode:
                config = self._app_mode.define_instance_configuration(app)
            else:
                config = DevelopmentConfig.configure_for_instance(app.instance_path)
        app.config.from_object(config)


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
