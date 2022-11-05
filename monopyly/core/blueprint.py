"""
Flask blueprint for core functionality.
"""
from flask import Blueprint


# Define the blueprint
bp = Blueprint('core', __name__)

# Import routes after defining blueprint to avoid circular imports
from . import routes
from . import context_processors
from . import filters
