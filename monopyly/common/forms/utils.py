"""
General utility objects for handling forms.
"""
from functools import wraps

from flask import flash
from wtforms.validators import ValidationError

from ...database import db
from ..utils import sort_by_frequency
from ._forms import form_err_msg


class Autocompleter:
    """
    A class to facilitate autocompletion.

    This is an object designed to facilitate autocompletion for a form.
    The autocompleter is used to define which form fields support
    autocompletion, and then manage the corresponding autocompletion
    lookups.

    Parameters
    ----------
    field_map : dict
        A mapping between fields supporting autocompletion and the model
        object that is used to access that field.
    """

    def __init__(self, field_map):
        self._field_map = field_map

    def autocomplete(self, field, **priority_sort_fields):
        """
        Provide autocomplete suggestions for the field.

        Given a form field name (which should match a database field),
        get potential entries that should be suggested as autocompletion
        options. Sort the suggestions by their frequency and return
        them.

        Parameters
        ----------
        field : str
            The name of the form field for which to provide
            autocompletion.
        priority_sort_field : dict
            A mapping of fields and a value of that field which will
            take precedence over a suggestion's frequency in the data
            when sorting the suggestions. The fields should be provided
            in order of increasing importance.

        Returns
        -------
        suggestions : list of str
            A list of autocompletion suggestions that are sorted by
            their frequency of appearance in the database.
        """
        model = self._field_map[field]
        suggestions = self._get_autocomplete_suggestions(model, field)
        for sort_field, precedence_value in priority_sort_fields.items():
            self._sort_suggestions_by_field(suggestions, model, field,
                                            sort_field, precedence_value)
        return suggestions

    @staticmethod
    def _get_autocomplete_suggestions(model, field):
        """Get autocomplete suggestions for a field."""
        # Get information from the database to use for autocompletion
        query = model.select_for_user(getattr(model, field))
        values = db.session.execute(query).scalars()
        suggestions = sort_by_frequency([value for value in values])
        return suggestions

    def _sort_suggestions_by_field(self, suggestions, model, field, sort_field,
                                   precedence_value):
        # Assume the user join will be sufficient
        sort_model = self._field_map[sort_field]
        sort_query = model.select_for_user(
            getattr(sort_model, sort_field),
            getattr(model, field),
        )
        field_value_by_sort_field = {}
        for row in db.session.execute(sort_query):
            value = row[field]
            # Register values associated with the important sort field value
            if not field_value_by_sort_field.get(value):
                row_has_precedence = (row[sort_field] == precedence_value)
                field_value_by_sort_field[value] = row_has_precedence
        suggestions.sort(key=field_value_by_sort_field.get, reverse=True)


def execute_on_form_validation(func):
    """A decorator that executes the function only if the form validates."""
    @wraps(func)
    def wrapper(form, *args, **kwargs):
        if form.validate():
            return func(form, *args, **kwargs)
        else:
            # Show an error to the user and print the errors for the admin
            flash(form_err_msg)
            print(form.errors)
            raise ValidationError("The form did not validate properly.")
    return wrapper

