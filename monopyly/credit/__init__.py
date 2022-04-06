"""
Flask blueprint for credit card financials.
"""
from flask import Blueprint


# Define the blueprint
credit_bp = Blueprint('credit', __name__, url_prefix='/credit')

from . import routes
