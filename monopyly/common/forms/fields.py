"""
General form constructions.
"""

from abc import ABC, abstractmethod

from dry_foundation.forms.validators import NumeralsOnly, SelectionNotBlank
from wtforms import fields as wtforms_fields
from wtforms.validators import Length
from wtforms.widgets import NumberInput

from ..utils import parse_date


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


class DatabaseSelectField(wtforms_fields.SelectField, ABC):
    """
    A select field that can auto-prepare choices from the database.

    Parameters
    ----------
    label : str
        The label of the field.
    validators : list or None
        A sequence of validators to call when ``validate`` is called.
    """

    # Value `-` ensures that the blank option will be the top choice
    # (before entry IDs)
    UNSET = "-"

    def __init__(self, label=None, validators=None, **kwargs):
        if not validators:
            validators = [SelectionNotBlank(blank=self.UNSET)]
        super().__init__(label=label, validators=validators, **kwargs)
        self.prepare_field_choices()

    @property
    def default_choices(self):
        return [(self.UNSET, "-")]

    @property
    @abstractmethod
    def _db_repo(self):
        raise NotImplementedError("Define the attribute in a subclass.")

    def process_data(self, value):
        """Process incoming data, and set the field default value."""
        value = self.UNSET if value is None else value
        super().process_data(value)

    def prepare_field_choices(self):
        """
        Prepare choices for a field in the form using the database.

        Using a reference to a database repository, this method queries the
        database for entries belonging to the user, and then uses those
        entries to populate the list of choices that may be selected
        for the field value.
        """
        self.choices = self.default_choices
        database_choices = [
            (str(entry.id), self._format_choice(entry))
            for entry in self._db_repo.get_entries()
        ]
        # Set the choices (for consistency, arbitrarily sort by entry ID)
        self.choices = sorted(self.default_choices + database_choices)

    @abstractmethod
    def _format_choice(self, entry):
        """
        Format a database entry field to display as a form field choice.

        Accepts an entry returned by the database repository, and extract a
        name to be displayed as a choice in the list of choices.
        """
        raise NotImplementedError("Define the formatting for a choice in a subclass.")


class CustomDatabaseSelectField(DatabaseSelectField):
    """A select field that can auto-prepare choices from the database."""

    # Value `__new___` ensures that the "new" option will be the bottom choice
    # (after entry IDs)
    NEW = "__new__"

    def __init__(self, label=None, validators=None, **kwargs):
        super().__init__(label=label, validators=validators, **kwargs)

    @property
    def default_choices(self):
        return [*super().default_choices, (self.NEW, f"New {self.label.text.lower()}")]
