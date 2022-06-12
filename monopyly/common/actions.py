"""Module describing logical actions (e.g. to be used in routes)."""


def get_user_database_entries(database_handler_type, *args, **kwargs):
    """Shortcut to get all entries (default fields) using a given handler."""
    db = database_handler_type()
    # Get all user entries from the database
    return db.get_entries()


def get_groupings(entries, lookup_db, fields=None):
    """
    Produce a dictionary where database entries are grouped.

    Parameters
    ----------
    entries : sqlite3.Row
        The entries to serve as the grouping guide.
    lookup_db : DatabaseHandler
        The database handler to use for acquiring grouped entries.
    fields : tuple, optional
        A subset of database fields to select when acquiring grouped
        entries via the database handler.

    Returns
    -------
    groupings : dict
        A mapping between each entry provided and the groupings of
        entries acquired by querying the database.
    """
    groupings = {}
    # Get all of the items from the lookup database matching each entry
    for entry in entries:
        grouping = lookup_db.get_entries((entry['id'],), fields=fields)
        if grouping:
            groupings[entry] = grouping
    return groupings


def delete_database_entry(database_handler_type, entry_id, return_field=None):
    """Delete an database entry; return a value if a field is specified."""
    db = database_handler_type()
    # Get the value of the specified field (pre-delete) to return if specified
    value = db.get_entry(entry_id)[return_field] if return_field else None
    # Remove the account from the database
    db.delete_entries((entry_id,))
    return value

