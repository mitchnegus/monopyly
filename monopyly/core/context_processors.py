"""
Filters defined for the application.
"""
from datetime import date

from .blueprint import bp


@bp.app_context_processor
def inject_date_today():
    """Inject a variable with today's date into the template context."""
    return dict(date_today=str(date.today()))

