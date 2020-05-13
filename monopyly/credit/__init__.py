"""
Flask blueprint for credit card financials.
"""
from flask import Blueprint


# Define the blueprint
credit = Blueprint('credit', __name__, url_prefix='/credit')

import monopyly.credit.routes
