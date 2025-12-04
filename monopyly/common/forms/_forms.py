"""
General form constructions.
"""

from abc import abstractmethod
from datetime import date

from dry_foundation.forms import AbstractFlaskForm, FlaskSubform
from wtforms.fields import StringField, SubmitField
from wtforms.validators import DataRequired

from .fields import CurrencyField, DateField

# Define a custom form error messaage
form_err_msg = "There was an improper value in your form. Please try again."


class EntryForm(AbstractFlaskForm):
    """
    A form designed to accept database entry information.

    This form is structured to accept information to be entered into the
    database. Each field must be either named to match a field in one
    of the database tables, or it must be a list of fields or a subform
    that follows the same naming schema.
    """

    def prepopulate(self, entry, data=None):
        """
        Generate a duplicate prepopulated form.

        Parameters
        ----------
        entry : database.models.Model
            A database entry from which to pull information for
            prepopulating the form.
        data : dict, optional
            A dictionary containing extra data that will be joined with
            data gathered from the given database entry. Fields defined
            in this data dictionary will supersed fields defined on the
            entry.

        Returns
        -------
        form : EntryForm
            A duplicate form, prepopulated with the collected database
            information.

        Notes
        -----
        WTForms requires that a form be instantiated in order to be
        able to properly introspect fields. Because of this, this method
        will only return a duplicate form matching the type of the
        form instance used to call it. Using the form's process method
        will not properly handle enumeration of field lists, so it
        can not be used as a replacement for populating an existing
        form.
        """
        entry_data = self.gather_entry_data(entry) if entry else {}
        # Merge data parsed from the entry with any data provided directly
        data = entry_data | (data or {})
        return self.__class__(data=data)

    @abstractmethod
    def gather_entry_data(self, entry):
        raise NotImplementedError(
            "Define how form data is gathered from an "
            "entry in a form-specific subclass."
        )

    @classmethod
    def _raise_gather_fail_error(cls, permissible_entries, entry):
        permissible_entries_string = ", ".join(
            [f"`{_.__name__}`" for _ in permissible_entries]
        )
        raise TypeError(
            f"Data for a `{cls.__name__}` can only be gathered from "
            f"permissible entry classes: {permissible_entries_string}; the "
            f"entry provided was a `{entry.__class__.__name__}` object."
        )


class EntrySubform(FlaskSubform, EntryForm):
    """A subform implementing ``EntryForm`` behavior."""


class AcquisitionSubform(EntrySubform):
    """
    A subform that acquires entries from the database based on inputs.

    This subform is intended to interface with the database to acquire
    database entries corresponding to the given criteria. A database
    handler must be defined in a subclass of this abstract class, and
    that handler is then used to get the
    """

    @property
    @abstractmethod
    def _db_handler(self):
        raise NotImplementedError("Define the attribute in a subclass.")

    def _produce_entry_from_field(self, form_entry_id_field_name):
        """Produce an entry matching an ID field in the subform data."""
        form_entry_id_field = getattr(self, form_entry_id_field_name)
        form_entry_id = int(form_entry_id_field.data)
        # If the entry is a new entry, create it from the form data
        if form_entry_id == 0:
            data = self._prepare_mapping()
            entry = self._db_handler.add_entry(**data)
            # Set the form field to match the newly added value
            form_entry_id_field.data = entry.id
        else:
            entry = self._db_handler.get_entry(form_entry_id)
        return entry

    @abstractmethod
    def _prepare_mapping(self):
        raise NotImplementedError("Prepare the mapping using a subclass.")


class TransactionForm(EntryForm):
    """An abstract form to input/edit generic transactions."""

    class SubtransactionSubform(EntrySubform):
        subtransaction_model = None
        # Fields pertaining to the subtransaction
        subtotal = CurrencyField("Amount", [DataRequired()])
        note = StringField("Note", [DataRequired()])
        tags = StringField("Tags")

        @property
        def subtransaction_data(self):
            """
            Produce a dictionary corresponding to a database subtransaction.
            """
            raw_tag_data = self.tags.data.split(",")
            data = {
                "subtotal": self.subtotal.data,
                "note": self.note.data,
                "tags": [tag.strip() for tag in raw_tag_data if tag],
            }
            return data

        def gather_entry_data(self, entry):
            if self.subtransaction_model is None:
                raise RuntimeError(
                    "A subtransaction model must be defined for every subtransaction "
                    "form."
                )
            elif isinstance(entry, self.subtransaction_model):
                return self._gather_subtransaction_data(entry)
            else:
                self._raise_gather_fail_error((self.subtransaction_model,), entry)

        def _gather_subtransaction_data(self, subtransaction):
            """Gather subtransaction-specific data."""
            tag_names = [tag.tag_name for tag in subtransaction.tags]
            data = {
                "subtotal": subtransaction.subtotal,
                "note": subtransaction.note,
                "tags": ", ".join(tag_names),
            }
            return data

    # Fields pertaining to the transaction
    transaction_date = DateField(
        "Transaction Date", validators=[DataRequired()], default=date.today
    )
    # Subtransactions should be defined as a `FieldList` in a subclass
    subtransactions = None
    submit = SubmitField("Save Transaction")
    # Define an autocompleter for the form (in a sublcass)
    _autocompleter = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.suggestions = {}

    def prepopulate(self, entry, data=None, suggestion_fields=()):
        """
        Generate a duplicate prepopulated form.

        Parameters
        ----------
        entry : database.models.Model
            A database entry from which to pull information for
            prepopulating the form.
        data : dict, optional
            A dictionary containing extra data that will be joined with
            data gathered from the given database entry. Fields defined
            in this data dictionary will supersed fields defined on the
            entry.
        suggestion_fields : list, optional
            A list with form-specific parameters defining how the form
            will extract and process a suggestion from the dictionary of
            data which will be added to the form.

        Returns
        -------
        form : TransactionForm
            A duplicate form, prepopulated with the collected database
            information.
        """
        self.suggestions |= self._extract_suggestions(data, suggestion_fields)
        form = super().prepopulate(entry, data=data)
        form.suggestions = self.suggestions
        return form

    def _extract_suggestions(self, data, suggestion_fields):
        # Extract suggestion field values from the given data as specified
        suggestions = {}
        for field in suggestion_fields:
            extraction_method = getattr(self, f"_extract_{field}_suggestion")
            suggestions[field] = extraction_method(data)
        return suggestions

    @staticmethod
    def _extract_suggestion(data, field):
        # Pop the field value to provide a suggestion, rather than a deduction
        return data.pop(field, None)

    def _prepare_transaction_data(self):
        subtransactions_data = [
            subform.subtransaction_data for subform in self["subtransactions"]
        ]
        data = {
            "internal_transaction_id": None,
            "transaction_date": self["transaction_date"].data,
            "merchant": self["merchant"].data,
            "subtransactions": subtransactions_data,
        }
        return data

    def _gather_transaction_data(self, transaction):
        """Gather transaction-specific data."""
        subtransactions_data = self._gather_subtransactions_data(
            transaction.subtransactions
        )
        data = {
            "transaction_date": transaction.transaction_date,
            "merchant": transaction.merchant,
            "subtransactions": subtransactions_data,
        }
        return data

    def _gather_subtransactions_data(self, subtransactions):
        """Gather subtransaction-specific data."""
        subtransactions_data = []
        for i, subtransaction in enumerate(subtransactions):
            # Use the subtransaction subform to gather data from the entry info
            #  - There will always be at least 1 subtransaction to use
            subtransactions_data.append(
                self.subtransactions[0].gather_entry_data(subtransaction)
            )
        return subtransactions_data

    @classmethod
    def autocomplete(cls, field, **priority_sort_fields):
        """Provide autocompletion suggestions for form fields."""
        return cls._autocompleter.autocomplete(field, **priority_sort_fields)
