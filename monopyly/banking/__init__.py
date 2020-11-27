"""
Flask blueprint for bank financials.
"""
from flask import Blueprint


# Define the blueprint
banking = Blueprint('banking', __name__, url_prefix='/banking')

from . import routes
