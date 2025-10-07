"""
Run the Monopyly app.
"""

from dry_foundation import DryFlask, Factory, interact

from .core.errors import render_error_template
from .database import SQLAlchemy


@Factory(db_interface=SQLAlchemy, echo_engine=False)
def create_app(config=None):
    """
    Create the Flask application.

    Create the Flask app, including configurations as specified. This
    will configure the app using the configuration objects made
    available by the Monopyly application and initialize the app
    by registering app blueprints, routes, and commands.
    """
    # Create and configure the app
    app = DryFlask(__name__, app_name="Monopyly")
    app.configure(config)
    # Register blueprints and error handlers specific to this app
    register_blueprints(app)
    register_errorhandlers(app)
    return app


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


def main():
    """The entry point to the Monopyly application."""
    interact(__name__)
