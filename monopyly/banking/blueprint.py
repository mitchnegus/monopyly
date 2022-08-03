"""
Flask blueprint for bank financials.
"""
from flask import Blueprint


# Define the blueprint
bp = Blueprint('banking', __name__, url_prefix='/banking')

# Import routes after defining blueprint to avoid circular imports
from . import routes
