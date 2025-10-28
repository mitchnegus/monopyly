"""
Flask blueprint for financial analytics.
"""

from flask import Blueprint

# Define the blueprint
bp = Blueprint("analytics", __name__, url_prefix="/analytics")

# Import routes after defining blueprint to avoid circular imports
from . import routes

__all__ = ["routes"]
