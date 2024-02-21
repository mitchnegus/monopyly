"""
Commonly shared form validators.
"""

from wtforms.validators import ValidationError


class NumeralsOnly:
    """
    Validates text contains only numerals.

    Parameters
    ----------
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
    ----------
    blank :
        The value representing a blank selection. The default is the
        integer `-1`.
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
