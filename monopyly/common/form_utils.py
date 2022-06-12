"""
General utility objects for handling forms.
"""
from abc import ABC, abstractmethod
from functools import wraps

from flask import flash
from flask_wtf import FlaskForm
from wtforms.fields import SelectField, FormField, FieldList
from wtforms.validators import ValidationError

from ..common.utils import sort_by_frequency
from ..db.handler.queries import validate_field


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

    def prepopulate(self, entry, **field_list_entries):
        """
        Prepopulate the form with the given database entry information.

        Parameters
        ----------
        entry : sqlite3.Row
            A database entry from which to pull information.
        **field_list_entries :
            Keyword arguments containing lists of database entries to
            use for pulling information for field list constructions.
            The keyword must be named to match the corresponding `FieldList`
            name.
        """
        data = self._get_form_data(entry, field_list_entries)
        self.process(data=data)

    def _get_form_data(self, entry, entry_lists):
        # Use the form fields (matching database fields) to get data
        form_data = {}
        for field in self:
            try:
                name, data = self._get_field_data(field, entry, entry_lists)
                form_data[name] = data
            except (IndexError, KeyError):
                # It is ok for data to not be found in the given entry
                # - KeyError thrown if key not in dict
                # - IndexError thrown if key not in sqlite3.Row
                pass
        return form_data

    def _get_field_data(self, field, entry, entry_lists):
        # In a subform field, the database name is only the last component
        field_name = field.name.split('-')[-1]
        if isinstance(field, FormField):
            field_data = field._get_form_data(entry, entry_lists)
        elif isinstance(field, FieldList):
            entry_list = entry_lists[field_name]
            field_data = self._get_field_list_data(field, entry_list,
                                                   entry_lists)
        else:
            field_data = entry[field_name]
        return field_name, field_data

    def _get_field_list_data(self, field_list, entry_list, entry_lists):
        # Use each entry list item to populate each field list item
        field_list_data = []
        for i, entry in enumerate(entry_list):
            # Add the field to the field list if it does not exist yet
            if i >= len(field_list):
                field_list.append_entry()
            field = field_list[i]
            name, data = self._get_field_data(field, entry, entry_lists)
            field_list_data.append(data)
        return field_list_data


class EntrySubform(EntryForm):
    """Subform disabling CSRF (CSRF is REQUIRED in encapsulating form)."""
    def __init__(self, *args, **kwargs):
        super().__init__(meta={'csrf': False}, *args, **kwargs)


class AcquisitionSubform(EntrySubform):
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


class Autocompleter(ABC):
    """
    A class to facilitate autocompletion.

    This object is an abstract base class designed to be subclassed by
    individual forms. The object will be customized to faciliate
    autocompletion for fields in that form as necessary.
    """


    @classmethod
    @property
    def autocompletion_fields(cls):
        return list(cls._autocompletion_handler_map.keys())

    @property
    @abstractmethod
    def _autocompletion_handler_map(cls):
        raise NotImplementedError("Define the attribute in a subclass.")

    @classmethod
    def autocomplete(cls, field):
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
        priority_sort_field : str
            A field in the database that will take precedence over
            frequency

        Returns
        -------
        suggestions : list of str
            A list of autocompletion suggestions that are sorted by
            their frequency of appearance in the database.
        """
        validate_field(field, cls.autocompletion_fields)
        # Get information from the database to use for autocompletion
        db = cls._autocompletion_handler_map[field]()
        entries = db.get_entries(fields=(field,))
        suggestions = sort_by_frequency([entry[field] for entry in entries])
        return suggestions


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

