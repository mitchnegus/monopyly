"""
Tools for interacting with internal transactions in the database.
"""

from flask import current_app
from sqlalchemy import insert


def add_internal_transaction():
    """Adds a new internal transaction to the database and returns its ID."""
    internal_transactions_table = current_app.db.tables["internal_transactions"]
    query = insert(internal_transactions_table)
    entry_id = current_app.db.session.execute(query).lastrowid
    return entry_id
