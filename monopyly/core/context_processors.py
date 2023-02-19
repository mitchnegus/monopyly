"""
Filters defined for the application.
"""
from datetime import date

from .blueprint import bp


@bp.app_context_processor
def inject_global_template_variables():
    """Inject template variablees globally into the template context."""
    template_globals = {
        "monopyly_version": "1.2.2.dev1",
        "copyright_statement": f"© {date.today().year}",
        "date_today": str(date.today()),
    }
    return template_globals
