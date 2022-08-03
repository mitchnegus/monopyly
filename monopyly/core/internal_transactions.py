"""
Tools for interacting with internal transactions in the database.
"""
from sqlalchemy import insert
from ..database import db


def add_internal_transaction():
    """Adds a new internal transaction to the database and returns its ID."""
    internal_transactions_table = db.tables['internal_transactions']
    query = insert(internal_transactions_table)
    entry_id = db.session.execute(query).lastrowid
    return entry_id

