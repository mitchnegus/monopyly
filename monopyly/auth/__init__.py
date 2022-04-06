"""
Flask blueprint for site authentication.
"""
from flask import Blueprint


# Define the blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

from . import routes
