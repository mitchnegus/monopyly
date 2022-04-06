"""
Flask blueprint for core functionality.
"""
from flask import Blueprint

# Define the blueprint
core_bp = Blueprint('core', __name__)

from . import routes
from . import filters
from . import context_processors
