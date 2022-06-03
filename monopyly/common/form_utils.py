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

    def form_generator(method):
        """Wrap a form method so that it generates (and returns) a form."""
        @classmethod
        def wrapper(cls, *args, **kwargs):
            # Instantiate the class to enable field structure introspection
            form = cls()
            method(form, *args, **kwargs)
            return form
        return wrapper

    @form_generator
    @abstractmethod
    def generate_new(self, *args, **kwargs):
        """
        Prepare a form to create a new database entry.

        Generate a form to create a new database entry. This form should
        be prepopulated with information from other entries specified by
        ID in the method arguments.

        Returns
        -------
        BankTransactionForm
            An instance of this class with any prepopulated information.

        Notes
        -----
        The `form_generator` decorator instantiates this class as a form
        instance before this method is run, passing that instance to
        this method. (Hence why the class is called like a class method,
        but uses `self` in the argument list).
        """
        self._prepare_new_data(*args, **kwargs)

    @abstractmethod
    def _prepare_new_data(self, *args, **kwargs):
        raise NotImplementedError("Use a derived class instead.")

    @form_generator
    @abstractmethod
    def generate_update(self, entry_id):
        """
        Prepare a form to update a database entry.

        Generate a form to update an existing database entry. This form
        should be prepopulated with all entry information that has been
        previously provided so that it can be updated.

        Parameters
        ----------
        entry_id : int
            The ID of the entry to be updated.

        Returns
        -------
        form : EntryForm
            An instance of this class with any prepopulated information.

        Notes
        -----
        The `form_generator` decorator instantiates this class as a form
        instance before this method is run, passing that instance to
        this method. (Hence why the class is called like a class method,
        but uses `self` in the argument list).
        """
        self._prepare_update_data(entry_id)

    @abstractmethod
    def _prepare_update_data(self, entry_id):
        raise NotImplementedError("Use a derived class instead.")

    def _get_data_from_entry(self, db_handler_type, entry_id):
        # Uses an entry (and database producing the entry) to load current data
        db = db_handler_type()
        entry = db.get_entry(entry_id)
        data = self._get_form_data(entry)
        return data

    def _get_form_data(self, entry):
        # Use the form fields (matching database fields) to get data
        form_data = {}
        for field in self:
            try:
                field_name, field_data = self._get_field_data(field, entry)
                form_data[field_name] = field_data
            except KeyError:
                pass
        return form_data

    def _get_field_data(self, field, entry):
        # In a subform field, the database name is only the last component
        field_name = field.name.split('-')[-1]
        if isinstance(field, FormField):
            field_data = field._get_form_data(entry)
        elif isinstance(field, FieldList):
            field_data = self._get_field_list_data(field, entry)
        else:
            field_data = entry[field_name]
        return field_name, field_data

    @abstractmethod
    def _get_field_list_data(self, field, entry):
        raise NotImplementedError("Field list behavior must currently be "
                                  "defined in a subclass as it is not "
                                  "generalizable.")


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

