"""
Flask blueprint for core functionality.
"""
from flask import Blueprint

# Define the blueprint
core = Blueprint('core', __name__)

import monopyly.core.routes
import monopyly.core.filters
import monopyly.core.context_processors
