"""
Flask blueprint for credit card financials.
"""

from flask import Blueprint

# Define the blueprint
bp = Blueprint("credit", __name__, url_prefix="/credit")

# Import routes after defining blueprint to avoid circular imports
from . import routes

__all__ = ["routes"]
