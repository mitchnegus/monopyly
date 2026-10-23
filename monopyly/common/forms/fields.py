"""
General form constructions.
"""

from dry_foundation.forms.fields import StrippedFieldMixin
from dry_foundation.forms.validators import NumeralsOnly
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


class StringField(StrippedFieldMixin, wtforms_fields.StringField):
    """A custom string field."""


class LastFourDigitsField(StringField):
    """A custom field for collecting the last four digits of cards/accounts."""

    def __init__(self, *args, validators=(), **kwargs):
        validators = list(validators)
        validators.extend([Length(4, 4), NumeralsOnly()])
        super().__init__(*args, validators=validators, **kwargs)
