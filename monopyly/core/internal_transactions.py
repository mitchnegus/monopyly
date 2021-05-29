"""
Tools for interacting with internal transactions in the database.
"""
from ..db import get_db


def add_internal_transaction(db=None):
    """Adds a new internal transaction to the database and returns its ID."""
    db = db if db else get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO internal_transactions DEFAULT VALUES")
    db.commit()
    entry_id = cursor.lastrowid
    return entry_id
