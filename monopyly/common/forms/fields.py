"""
General form constructions.
"""

from abc import ABC, abstractmethod

from wtforms import fields as wtforms_fields
from wtforms.validators import Length
from wtforms.widgets import NumberInput

from ..utils import parse_date
from .validators import NumeralsOnly, SelectionNotBlank


class DateField(wtforms_fields.DateField):
    """A date field with better parsing abilities than the WTForms default."""

    def __init__(self, *args, filters=(), **kwargs):
        # The date field should normally handle date conversion, but this
        # filter remains as a backup for browsers not supporting locales
        if parse_date not in filters:
            filters = list(filters)
            filters.append(parse_date)
        super().__init__(*args, filters=filters, **kwargs)


class CurrencyField(wtforms_fields.DecimalField):
    """A decimal field with currency-specific customizations."""

    widget = NumberInput(step=0.01)

    def __init__(self, *args, filters=(), **kwargs):
        filters = list(filters)
        filters.append(lambda x: float(round(x, 2)) if x else None)
        super().__init__(*args, filters=filters, places=2, **kwargs)


class StringField(wtforms_fields.StringField):
    """A custom string field."""

    def __init__(self, *args, filters=(), **kwargs):
        filters = list(filters)
        filters.append(lambda x: x.strip() if x else None)
        super().__init__(*args, filters=filters, **kwargs)


class LastFourDigitsField(StringField):
    """A custom field for collecting the last four digits of cards/accounts."""

    def __init__(self, *args, validators=(), **kwargs):
        validators = list(validators)
        validators.extend([Length(4, 4), NumeralsOnly()])
        super().__init__(*args, validators=validators, **kwargs)


class CustomChoiceSelectField(wtforms_fields.SelectField, ABC):
    """A select field that can auto-prepare choices."""

    def __init__(self, label=None, validators=None, coerce=int, **kwargs):
        if not validators:
            validators = [SelectionNotBlank()]
        super().__init__(label=label, validators=validators, coerce=int, **kwargs)
        self.prepare_field_choices()

    def process_data(self, value):
        """Process incoming data, and set the field default value."""
        value = -1 if value is None else value
        super().process_data(value)

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
        self.choices = [(-1, "-"), (0, f"New {self.label.text.lower()}")]
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
        raise NotImplementedError("Define the formatting for a choice in a subclass.")
