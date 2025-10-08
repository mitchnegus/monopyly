"""
Flask blueprint for site authentication.
"""

from flask import Blueprint

# Define the blueprint
bp = Blueprint("auth", __name__, url_prefix="/auth")

# Import routes after defining blueprint to avoid circular imports
from . import routes

__all__ = ["routes"]
