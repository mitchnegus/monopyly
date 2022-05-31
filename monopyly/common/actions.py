"""Module describing logical actions (e.g. to be used in routes)."""


def get_user_database_entries(database_handler_type, *args, **kwargs):
    """Shortcut to get all entries (default fields) using a given handler."""
    db = database_handler_type()
    # Get all user entries from the database
    return db.get_entries()


def delete_database_entry(database_handler_type, entry_id, return_field=None):
    """Delete an database entry; return a value if a field is specified."""
    db = database_handler_type()
    # Get the value of the specified field (pre-delete) to return if specified
    value = db.get_entry(entry_id)[return_field] if return_field else None
    # Remove the account from the database
    db.delete_entries((entry_id,))
    return value

