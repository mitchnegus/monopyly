"""
Flask blueprint for core functionality.
"""
from flask import Blueprint

# Define the blueprint
bp = Blueprint("core", __name__)

# Import routes after defining blueprint to avoid circular imports
from . import context_processors, filters, routes
