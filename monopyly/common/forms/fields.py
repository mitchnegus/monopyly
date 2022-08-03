"""
General form constructions.
"""
from abc import ABC, abstractmethod

from flask_wtf import FlaskForm
from wtforms.fields import SelectField, FormField, FieldList

from ...banking.banks import BankHandler
from .validators import SelectionNotBlank


class CustomChoiceSelectField(SelectField, ABC):
    """A select field that can auto-prepare choices."""

    def __init__(self, label=None, validators=None, coerce=int, **kwargs):
        if not validators:
            validators = [SelectionNotBlank()]
        super().__init__(label=label, validators=validators, **kwargs)
        self.prepare_field_choices()

    @property
    @abstractmethod
    def _db_handler(self):
        raise NotImplementedError("Define the attribute in a subclass.")

    def prepare_field_choices(self):
        """
        Prepare choices for a field in the form using the database.

        Using a reference to a database handler, this method queries the
        database for entries belonging to the user, and then uses those
        entries to populate the list of choices that may be selected
        for the field value.
        """
        # Collect all available user entries
        entries = self._db_handler.get_entries()
        # Set default choice values
        self.choices = [(-1, "-"),
                         (0, f"New {self.label.text.lower()}")]
        # Set the user choices (for consistency, arbitrarily sort by entry ID)
        for entry in sorted(entries, key=lambda entry: entry.id):
            display_name = self._format_choice(entry)
            self.choices.insert(-1, (entry.id, display_name))

    @abstractmethod
    def _format_choice(self, entry):
        """
        Format a database entry field to display as a form field choice.

        Accepts an entry returned by the database handler, and extract a
        name to be displayed as a choice in the list of choices.
        """
        raise NotImplementedError("Define the formatting for a choice in a "
                                  "subclass.")

