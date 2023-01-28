"""
A database handler for facilitating interactions with the SQLite database.
"""
from abc import ABC, abstractmethod

from flask import current_app, g
from werkzeug.exceptions import abort
from sqlalchemy import inspect
from sqlalchemy.exc import NoResultFound

from .utils import validate_sort_order


class DatabaseHandler(ABC):
    """
    A generic handler for database access.

    Database handlers simplify commonly used database interactions.
    Complicated queries can be reformulated as class methods, taking
    variable arguments. The handler also performs user authentication
    upon creation so that user authentication is not required for each
    query.

    Attributes
    ----------
    user_id : int
        The ID of the user who is the subject of database access.
    model : type
        The type of database model that the handler is primarily
        designed to manage.
    table : str
        The name of the database table that this handler manages.
    """

    @classmethod
    @property
    def _db(cls):
        return current_app.db

    @classmethod
    @property
    def user_id(cls):
        return g.user.id

    @classmethod
    @property
    @abstractmethod
    def model(cls):
        # The handler must have a defined model
        raise NotImplementedError("Define a model in a subclass.")

    @classmethod
    @property
    def table(cls):
        return cls.model.__tablename__

    @staticmethod
    def _filter_value(field, value):
        # Build a filter based on the values (if given)
        if value is None:
            return None
        return (field == value)

    @staticmethod
    def _filter_values(field, values):
        # Build a filter based on the values (if given)
        if values is None:
            return None
        return field.in_(values)

    @classmethod
    def get_entries(cls, *filters, sort_order=None):
        """
        Retrieve a set of entries from the database.

        Executes a simple query to select the table entries from
        the database which match the given filters.

        Parameters
        ----------
        *filters :
            Criteria to use when applying filters to the query.
            (A filter with a value of `None` will be ignored.)
        sort_order : ...
            ...

        Returns
        -------
        entries : list of database.models.Model
            Models containing matching entries from the database.
        """
        # Ignore all filters with `None` values
        filters = [_ for _ in filters if _ is not None]
        # Query entries for the authorized user
        query = cls.model.select_for_user()
        query = cls._customize_entries_query(query, filters, sort_order)
        entries = cls._db.session.execute(query).scalars()
        return entries

    @classmethod
    def find_entry(cls, *filters, sort_order=None, require_unique=True):
        """
        Find an entry using uniquely identifying characteristics.

        Parameters
        ----------
        *filters :
            Criteria to use when applying filters to the query.
            (If all criteria are `None`, the returned entry will be
            `None`.)
        sort_order : str
            The order to use when sorting values returned by the
            database query.
        require_unique : bool
            A flag indicating whether a found entry must be the one and
            only entry matching the criteria. The default is `True`, and
            if an entry is not the only one matching the criteria, an
            error is raised.

        Returns
        -------
        entry : database.models.Model
            A model containing a matching entry from the database.
        """
        # Ignore all filters with `None` values; return `None` with no criteria
        filters = [_ for _ in filters if _ is not None]
        if not filters:
            return None
        # Query entries from the authorized user
        query = cls.model.select_for_user()
        query = cls._customize_entries_query(query, filters, sort_order)
        results = cls._db.session.execute(query)
        if require_unique:
            entry = results.scalar_one_or_none()
        else:
            entry = results.scalar()
        return entry

    @classmethod
    def _customize_entries_query(cls, query, filters, sort_order):
        """
        Customize a query to retrieve entries from the database.

        Notes
        -----
        As an implementation detail, the query returned by this method
        defined in the lowest level subclass should always be the final
        query executed by the current `Session` object in the
        `get_entries` method.
        """
        return cls._filter_entries(query, filters)

    @staticmethod
    def _filter_entries(query, filters):
        """Apply filters to a query."""
        return query.filter(*filters)

    @classmethod
    def _sort_query(cls, query, *column_orders):
        """
        Sort a query on the given column(s).

        Parameters
        ----------
        query : sqlalchemy.sql.expression.Select
            The query to be sorted.
        column_orders : tuple
            Any number of pairs consisting of a table column and a
            string giving the sorting order for that column.
        """
        for column, sort_order in column_orders:
            if sort_order:
                validate_sort_order(sort_order)
                if sort_order == "DESC":
                    order_column = column.desc()
                else:
                    order_column = column.asc()
                query = query.order_by(order_column)
        return query

    @classmethod
    def get_entry(cls, entry_id):
        """
        Retrieve a single entry from the database.

        Executes a simple query from the database to get a single entry
        by ID.

        Parameters
        ----------
        entry_id : int
            The ID of the entry to be found.

        Returns
        -------
        entry : database.models.Model
            A model containing a matching entry from the database.
        """
        criteria = [cls.model.id == entry_id]
        query = cls.model.select_for_user().where(*criteria)
        try:
            entry = cls._db.session.execute(query).scalar_one()
        except NoResultFound:
            abort_msg = (f"The entry with ID {entry_id} does not exist for "
                          "the current user.")
            abort(404, abort_msg)
        return entry

    @classmethod
    def add_entry(cls, **field_values):
        """
        Create a new entry in the database given field values.

        Parameters
        ----------
        **field_values :
            Values for each field in the entry.

        Returns
        -------
        entry : database.models.Model
            The saved entry.
        """
        entry = cls.model(**field_values)
        cls._db.session.add(entry)
        cls._db.session.flush()
        # Confirm that this was an authorized entry by the user
        entry = cls.get_entry(entry.id)
        return entry

    @classmethod
    def update_entry(cls, entry_id, **field_values):
        """
        Update an entry in the database given field values.

        Accept a mapping relating given inputs to database fields. This
        mapping is used to update an existing entry in the database. All
        fields are sanitized prior to updating.

        Parameters
        ----------
        entry_id : int
            The ID of the entry to be updated.
        **field_values :
            Values for fields to update in the entry.

        Returns
        -------
        entry : database.models.Model
            The saved entry.
        """
        cls._confirm_manipulation_authorization(entry_id)
        entry = cls._db.session.get(cls.model, entry_id)
        entry_fields = [column.name for column in inspect(cls.model).columns]
        for field, value in field_values.items():
            if field not in entry_fields:
                raise ValueError("A value cannot be updated in the "
                                f"nonexistent field {field}.")
            setattr(entry, field, value)
        cls._db.session.flush()
        # Confirm that this was an authorized entry by the user
        entry = cls.get_entry(entry.id)
        return entry

    @classmethod
    def delete_entry(cls, entry_id):
        """
        Delete an entry in the database given its ID.

        Parameters
        ----------
        entry_id : int
            The ID of the entry to be deleted.
        """
        cls._confirm_manipulation_authorization(entry_id)
        entry = cls._db.session.get(cls.model, entry_id)
        cls._db.session.delete(entry)
        cls._db.session.flush()

    @classmethod
    def _confirm_manipulation_authorization(cls, entry_id):
        # Confirm (via access) that the user may manipulate the entry
        return cls.get_entry(entry_id)


class DatabaseViewHandler(DatabaseHandler):
    """
    A generic handler for database view access.

    The view handler imitates the behavior of the standard database
    handler, but with minor customizations to allow the handler to
    operate on database views, rather than native tables.
    """
    _view_context = False

    @classmethod
    @property
    @abstractmethod
    def _model(cls):
        # The handler must have a defined model as the primary base of the view
        None

    @classmethod
    @property
    @abstractmethod
    def _model_view(cls):
        # The handler must have a defined model view
        raise NotImplementedError("Define a model in a subclass.")

    @classmethod
    @property
    def model(cls):
        return cls._model_view if cls._view_context else cls._model

    @classmethod
    @property
    def table(cls):
        return cls._model.__tablename__

    @classmethod
    @property
    def table_view(cls):
        return cls._model_view.__tablename__

    def view_query(func):
        """Require that a function use a model view rather than the model."""
        def wrapper(cls, *args, **kwargs):
            orig_view_context = cls._view_context
            cls._view_context = True
            try:
                return_value = func(cls, *args, **kwargs)
            finally:
                cls._view_context = orig_view_context
            return return_value
        return wrapper

    @classmethod
    @view_query
    def get_entries(cls, *filters, sort_order=None):
        return super().get_entries(*filters, sort_order=sort_order)

    @classmethod
    @view_query
    def find_entry(cls, *filters, sort_order=None, require_unique=True):
        return super().find_entry(
            *filters, sort_order=sort_order, require_unique=require_unique
        )

    @classmethod
    @view_query
    def get_entry(cls, entry_id):
        return super().get_entry(entry_id)

