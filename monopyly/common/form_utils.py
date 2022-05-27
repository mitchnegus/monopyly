"""
General utility objects for handling forms.
"""
from abc import ABC, abstractmethod
from functools import wraps

from flask import flash
from flask_wtf import FlaskForm
from wtforms.fields import SelectField
from wtforms.validators import ValidationError


# Define a custom form error messaage
form_err_msg = "There was an improper value in your form. Please try again."


class FlaskSubForm(FlaskForm):
    """Subform disabling CSRF (CSRF is REQUIRED in encapsulating form)."""
    def __init__(self, *args, **kwargs):
        super().__init__(meta={'csrf': False}, *args, **kwargs)


class AbstractSubformMixinMeta(type(FlaskSubForm), ABC):
    # Defined to allow the subforms to also to be abstract base classes
    pass


class AcquisitionSubForm(FlaskSubForm, metaclass=AbstractSubformMixinMeta):
    """Subform that facilitates acquisition based on data and the database."""

    @property
    @abstractmethod
    def _db_handler_type(self):
        raise NotImplementedError("Define the attribute in a subclass.")

    @property
    def db(self):
        return self._db_handler_type()

    def get_entry(self, form_entry_id, creation=True):
        """Get (or optionally create) an entry matching the subform data."""
        # Check if the entry exists and potentially create it if not
        if form_entry_id == 0:
            if creation:
                # Add the entry to the database if it does not yet exist
                data = self._prepare_mapping()
                entry = self.db.add_entry(data)
            else:
                entry = None
        else:
            entry = self.db.get_entry(form_entry_id)
        return entry

    @abstractmethod
    def _prepare_mapping(self):
        raise NotImplementedError("Prepare the mapping using a subclass.")



class CustomChoiceSelectField(SelectField, ABC):
    """A select field that can auto-prepare choices."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prepare_field_choices()

    @property
    @abstractmethod
    def _db_handler_type(self):
        raise NotImplementedError("Define the attribute in a subclass.")

    @property
    def db(self):
        return self._db_handler_type()

    def prepare_field_choices(self):
        """
        Prepare choices for a field in the form using the database.

        Using a reference to a database handler, this method queries the
        database for entries belonging to the user, and then uses those
        entries to populate the list of choices that may be selected
        for the field value.
        """
        # Collect all available user entries
        entries = self.db.get_entries()
        # Set default choice values
        self.choices = [(-1, "-"),
                         (0, f"New {self.label.text.lower()}")]
        # Set the user choices
        for entry in entries:
            display_name = self._format_choice(entry)
            # Insert at second-to-last position (before 'New ____')
            self.choices.insert(-1, (entry['id'], display_name))

    @abstractmethod
    def _format_choice(self, entry):
        """
        Format a database entry field to display as a form field choice.

        Accepts an entry returned by the database handler, and extract a
        name to be displayed as a choice in the list of choices.
        """
        raise NotImplementedError("Define the formatting for a choice in a "
                                  "subclass.")


class NumeralsOnly:
    """
    Validates text contains only numerals.

    Parameters
    ––––––––––
    message : str
        Error message to raise in case of a validation error.
    """

    def __init__(self, message=None):
        if not message:
            message = "Field can only contain numerals."
        self.message = message

    def __call__(self, form, field):
        try:
            int(field.data)
        except ValueError:
            raise ValidationError(self.message)


class SelectionNotBlank:
    """
    Validates that a selection is not a blank submission.

    Parameters
    ––––––––––
    blank : int
        The integer representing a blank selection.
    message : str
        Error message to raise in case of a validation error.
    """

    def __init__(self, blank=-1, message=None):
        self.blank = blank
        if not message:
            message = "A selection must be made."
        self.message = message

    def __call__(self, form, field):
        if field.data == self.blank:
            raise ValidationError(self.message)


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

