"""
General form constructions.
"""
from abc import ABC, abstractmethod

from flask_wtf import FlaskForm
from wtforms.fields import (
    SelectField, FormField, FieldList, DecimalField, StringField, SubmitField
)
from wtforms.validators import DataRequired

from ..utils import parse_date
from .validators import SelectionNotBlank


# Define a custom form error messaage
form_err_msg = "There was an improper value in your form. Please try again."


class AbstractEntryFormMixinMeta(type(FlaskForm), ABC):
    # Defined to allow the forms to also to be abstract base classes
    pass


class EntryForm(FlaskForm, metaclass=AbstractEntryFormMixinMeta):
    """
    A form designed to accept database entry information.

    This form is structured to accept information to be entered into the
    database. Each field must be either named to match a field in one
    of the database tables, or it must be a list of fields or a subform
    that follows the same naming schema.
    """

    def prepopulate(self, entry):
        """
        Prepopulate the form with the given database entry information.

        Parameters
        ----------
        entry : database.models.Model
            A database entry from which to pull information for
            prepopulating the form.
        """
        data = self.gather_entry_data(entry)
        self.process(data=data)

    @abstractmethod
    def gather_entry_data(self, entry):
        raise NotImplementedError("Define how form data is gathered from an "
                                  "entry in a form-specific subclass.")

    def _raise_gather_fail_error(self, permissible_entries, entry):
        permissible_entries_string = ", ".join([
            f"`{_.__name__}`" for _ in permissible_entries
        ])
        raise TypeError(
            f"Data for a `{self.__class__.__name__}` can only be gathered "
            f"from permissible entry classes: {permissible_entries_string}; "
            f"the entry provided was a `{entry.__class__.__name__}` object."
        )


class EntrySubform(EntryForm):
    """Subform disabling CSRF (CSRF is REQUIRED in encapsulating form)."""
    def __init__(self, *args, **kwargs):
        super().__init__(meta={"csrf": False}, *args, **kwargs)


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
        # Fields pertaining to the subtransaction
        subtotal = DecimalField(
            "Amount",
            validators=[DataRequired()],
            filters=[lambda x: float(round(x, 2)) if x else None],
            places=2,
        )
        note = StringField("Note", [DataRequired()])

        @property
        def subtransaction_data(self):
            data = {
                "subtotal": self.subtotal.data,
                "note": self.note.data,
            }
            return data

        @abstractmethod
        def gather_entry_data(self, entry):
            raise NotImplementedError("Define how subtransaction data is "
                                      "gathered from an entry in a subclass.")

    # Fields pertaining to the transaction
    transaction_date = StringField(
        "Transaction Date",
        validators=[DataRequired()],
        filters=[parse_date]
    )
    # Subtransactions should be defined as a `FieldList` in a subclass
    subtransactions = None
    submit = SubmitField("Save Transaction")
    # Define an autocompleter for the form (in a sublcass)
    _autocompleter = None

    def _prepare_transaction_data(self):
        subtransactions_data =  [
            subform.subtransaction_data for subform in self["subtransactions"]
        ]
        data = {
            "internal_transaction_id": None,
            "transaction_date": self["transaction_date"].data,
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
            "subtransactions": subtransactions_data,
        }
        return data

    def _gather_subtransactions_data(self, subtransactions):
        """Gather subtransaction-specific data."""
        subtransactions_data = []
        for i, subtransaction in enumerate(subtransactions):
            # Add a subtransaction subform if necessary
            if i+1 > len(self.subtransactions):
                self.subtransactions.append_entry()
            # Use the subtransaction subform to gather data from the entry info
            subtransactions_data.append(
                self.subtransactions[i].gather_entry_data(subtransaction)
            )
        return subtransactions_data

    @classmethod
    def autocomplete(cls, field, **priority_sort_fields):
        """Provide autocompletion suggestions for form fields."""
        return cls._autocompleter.autocomplete(field, **priority_sort_fields)

