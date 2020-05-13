"""
Flask blueprint for site authentication.
"""
from flask import Blueprint


# Define the blueprint
auth = Blueprint('auth', __name__, url_prefix='/auth')

import monopyly.auth.routes
